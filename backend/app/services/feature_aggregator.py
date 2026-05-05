"""Redis feature aggregator — rolling 30-day windows per employee."""

from __future__ import annotations

import json
import time
from typing import Any

import redis.asyncio as aioredis
import structlog

log = structlog.get_logger()

WINDOW_SECONDS = 30 * 24 * 3600  # 30 days


class FeatureAggregator:
    def __init__(self, redis: aioredis.Redis) -> None:
        self._r = redis

    def _key(self, employee_id: str, field: str) -> str:
        return f"hawkeye:emp:{employee_id}:{field}"

    async def update(self, employee_id: str, event: dict[str, Any]) -> None:
        """Update rolling aggregates for one event."""
        now = time.time()
        pipe = self._r.pipeline()

        amount = float(event.get("amount", 0) or 0)
        txn_type = str(event.get("txn_type", ""))
        is_negative = amount < 0 or txn_type in ("reversal", "debit")
        is_sub49k = 0 < amount < 49_000

        # Increment counters
        pipe.incr(self._key(employee_id, "n"))
        pipe.incrbyfloat(self._key(employee_id, "sa"), amount)
        pipe.expire(self._key(employee_id, "n"), WINDOW_SECONDS)
        pipe.expire(self._key(employee_id, "sa"), WINDOW_SECONDS)

        if is_negative:
            pipe.incr(self._key(employee_id, "ngt"))
            pipe.expire(self._key(employee_id, "ngt"), WINDOW_SECONDS)

        if is_sub49k:
            pipe.incr(self._key(employee_id, "s49"))
            pipe.incrbyfloat(self._key(employee_id, "s49_sum"), amount)
            pipe.expire(self._key(employee_id, "s49"), WINDOW_SECONDS)
            pipe.expire(self._key(employee_id, "s49_sum"), WINDOW_SECONDS)

        # Counterparties (HyperLogLog for cardinality)
        cp = event.get("counterparty_id", event.get("system_resource", ""))
        if cp:
            pipe.pfadd(self._key(employee_id, "nc_hll"), cp)
            pipe.expire(self._key(employee_id, "nc_hll"), WINDOW_SECONDS)
            if amount > 0:
                pipe.pfadd(self._key(employee_id, "ncp_c_hll"), cp)
                pipe.expire(self._key(employee_id, "ncp_c_hll"), WINDOW_SECONDS)
            else:
                pipe.pfadd(self._key(employee_id, "ncp_d_hll"), cp)
                pipe.expire(self._key(employee_id, "ncp_d_hll"), WINDOW_SECONDS)

        # Balance tracking
        balance = float(event.get("balance", amount) or amount)
        bal_key = self._key(employee_id, "bal_min")
        pipe.set(bal_key, min(balance, await self._get_float(bal_key) or balance))
        pipe.expire(bal_key, WINDOW_SECONDS)

        # Track pass/fail (pass = amount > 0, not reversed)
        is_pass = not is_negative
        pipe.incr(self._key(employee_id, "pass_count" if is_pass else "fail_count"))
        pipe.expire(self._key(employee_id, "pass_count"), WINDOW_SECONDS)
        pipe.expire(self._key(employee_id, "fail_count"), WINDOW_SECONDS)

        # Event count for scoring trigger
        pipe.incr(self._key(employee_id, "event_count"))

        await pipe.execute()

    async def _get_float(self, key: str) -> float | None:
        v = await self._r.get(key)
        return float(v) if v is not None else None

    async def get_features(self, employee_id: str) -> dict[str, float]:
        """Retrieve aggregated features as a feature dict."""
        pipe = self._r.pipeline()
        keys = ["n", "sa", "ngt", "s49", "s49_sum", "pass_count", "fail_count", "bal_min"]
        for k in keys:
            pipe.get(self._key(employee_id, k))
        pipe.pfcount(self._key(employee_id, "nc_hll"))
        pipe.pfcount(self._key(employee_id, "ncp_c_hll"))
        pipe.pfcount(self._key(employee_id, "ncp_d_hll"))

        results = await pipe.execute()
        vals = {k: (float(results[i]) if results[i] is not None else 0.0) for i, k in enumerate(keys)}
        nc = float(results[len(keys)]) if results[len(keys)] else 0.0
        ncp_c = float(results[len(keys) + 1]) if results[len(keys) + 1] else 0.0
        ncp_d = float(results[len(keys) + 2]) if results[len(keys) + 2] else 0.0

        n = vals["n"] or 1.0
        ngt = vals["ngt"]
        s49 = vals["s49"]
        pass_count = vals["pass_count"]
        fail_count = vals["fail_count"]

        pngt = ngt / n
        ps49 = s49 / n
        pass_rate = pass_count / (pass_count + fail_count) if (pass_count + fail_count) > 0 else 1.0
        fan_ratio = (ncp_c / ncp_d) if ncp_d > 0 else ncp_c

        return {
            "n": vals["n"],
            "sa": vals["sa"],
            "nc": nc,
            "ngt": ngt,
            "s49": s49,
            "pngt": pngt,
            "ps49": ps49,
            "pass_rate": pass_rate,
            "fan_ratio": fan_ratio,
            "bal_min": vals["bal_min"],
            "ncp_c": ncp_c,
            "ncp_d": ncp_d,
            "mule_ip_match": 0.0,  # not available from event stream
        }

    async def get_event_count(self, employee_id: str) -> int:
        v = await self._r.get(self._key(employee_id, "event_count"))
        return int(v) if v else 0
