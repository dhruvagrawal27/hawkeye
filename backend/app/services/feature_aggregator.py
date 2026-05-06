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
        abs_amount = abs(amount)
        txn_type = str(event.get("txn_type", "D"))
        is_negative = amount < 0 or txn_type in ("reversal", "debit", "D")
        is_sub49k = 0 < abs_amount < 49_000
        is_sub45k = 0 < abs_amount < 45_000

        # Increment counters
        pipe.incr(self._key(employee_id, "n"))
        pipe.incrbyfloat(self._key(employee_id, "sa"), abs_amount)
        pipe.expire(self._key(employee_id, "n"), WINDOW_SECONDS)
        pipe.expire(self._key(employee_id, "sa"), WINDOW_SECONDS)

        # Sum of squares for std deviation estimate
        pipe.incrbyfloat(self._key(employee_id, "sa2"), abs_amount * abs_amount)
        pipe.expire(self._key(employee_id, "sa2"), WINDOW_SECONDS)

        if is_negative:
            pipe.incr(self._key(employee_id, "ngt"))
            pipe.expire(self._key(employee_id, "ngt"), WINDOW_SECONDS)

        if is_sub49k:
            pipe.incr(self._key(employee_id, "s49"))
            pipe.incrbyfloat(self._key(employee_id, "s49_sum"), abs_amount)
            pipe.expire(self._key(employee_id, "s49"), WINDOW_SECONDS)
            pipe.expire(self._key(employee_id, "s49_sum"), WINDOW_SECONDS)

        if is_sub45k:
            pipe.incr(self._key(employee_id, "s45"))
            pipe.expire(self._key(employee_id, "s45"), WINDOW_SECONDS)

        # Amount-range buckets
        for threshold, label in [(1000, "pr1k"), (5000, "pr5k"), (10000, "pr10k"),
                                   (25000, "pr25k"), (50000, "pr50k")]:
            if abs_amount > threshold:
                pipe.incr(self._key(employee_id, label))
                pipe.expire(self._key(employee_id, label), WINDOW_SECONDS)

        # Large/XL buckets
        if abs_amount > 100_000:
            pipe.incr(self._key(employee_id, "pxlg"))
            pipe.expire(self._key(employee_id, "pxlg"), WINDOW_SECONDS)
        if abs_amount > 50_000:
            pipe.incr(self._key(employee_id, "plrg"))
            pipe.expire(self._key(employee_id, "plrg"), WINDOW_SECONDS)

        # Counterparties (HyperLogLog for cardinality)
        cp = event.get("counterparty_id") or event.get("system_resource", "")
        if cp:
            pipe.pfadd(self._key(employee_id, "nc_hll"), cp)
            pipe.expire(self._key(employee_id, "nc_hll"), WINDOW_SECONDS)
            if amount > 0:
                pipe.pfadd(self._key(employee_id, "ncp_c_hll"), cp)
                pipe.expire(self._key(employee_id, "ncp_c_hll"), WINDOW_SECONDS)
            else:
                pipe.pfadd(self._key(employee_id, "ncp_d_hll"), cp)
                pipe.expire(self._key(employee_id, "ncp_d_hll"), WINDOW_SECONDS)

        # Distinct channels
        channel = event.get("channel", "")
        if channel:
            pipe.pfadd(self._key(employee_id, "nch_hll"), channel)
            pipe.expire(self._key(employee_id, "nch_hll"), WINDOW_SECONDS)

        # Distinct MCC codes
        mcc = event.get("mcc_code", "")
        if mcc:
            pipe.pfadd(self._key(employee_id, "nmcc_hll"), mcc)
            pipe.expire(self._key(employee_id, "nmcc_hll"), WINDOW_SECONDS)

        # Distinct IPs (n_unique_ips)
        ip = event.get("ip_address") or event.get("workstation_ip", "")
        if ip:
            pipe.pfadd(self._key(employee_id, "nip_hll"), ip)
            pipe.expire(self._key(employee_id, "nip_hll"), WINDOW_SECONDS)

        # Balance tracking — event field is balance_after_transaction
        balance = float(
            event.get("balance_after_transaction")
            or event.get("balance")
            or abs_amount
            or 0
        )
        bal_min_key = self._key(employee_id, "bal_min")
        bal_max_key = self._key(employee_id, "bal_max")
        cur_min = await self._get_float(bal_min_key)
        cur_max = await self._get_float(bal_max_key)
        pipe.set(bal_min_key, min(balance, cur_min) if cur_min is not None else balance)
        pipe.set(bal_max_key, max(balance, cur_max) if cur_max is not None else balance)
        pipe.expire(bal_min_key, WINDOW_SECONDS)
        pipe.expire(bal_max_key, WINDOW_SECONDS)
        pipe.incrbyfloat(self._key(employee_id, "bal_sum"), balance)
        pipe.expire(self._key(employee_id, "bal_sum"), WINDOW_SECONDS)

        # Track pass/fail (pass = credit, not reversed)
        is_pass = not is_negative
        pipe.incr(self._key(employee_id, "pass_count" if is_pass else "fail_count"))
        pipe.expire(self._key(employee_id, "pass_count"), WINDOW_SECONDS)
        pipe.expire(self._key(employee_id, "fail_count"), WINDOW_SECONDS)

        # After-hours / weekend flags  → map to model feature names: hrs, pwkd
        if event.get("is_after_hours"):
            pipe.incr(self._key(employee_id, "n_after_hours"))
            pipe.expire(self._key(employee_id, "n_after_hours"), WINDOW_SECONDS)
        if event.get("is_weekend"):
            pipe.incr(self._key(employee_id, "n_weekend"))
            pipe.expire(self._key(employee_id, "n_weekend"), WINDOW_SECONDS)

        # Records accessed (data exfiltration proxy)
        records = float(event.get("records_accessed", 0) or 0)
        if records > 0:
            pipe.incrbyfloat(self._key(employee_id, "records_sum"), records)
            pipe.expire(self._key(employee_id, "records_sum"), WINDOW_SECONDS)

        # Max amount
        amt_key = self._key(employee_id, "mx")
        amt_min_key = self._key(employee_id, "amt_min")
        cur_mx = await self._get_float(amt_key)
        cur_mn = await self._get_float(amt_min_key)
        if cur_mx is None or abs_amount > cur_mx:
            pipe.set(amt_key, abs_amount)
            pipe.expire(amt_key, WINDOW_SECONDS)
        if cur_mn is None or abs_amount < cur_mn:
            pipe.set(amt_min_key, abs_amount)
            pipe.expire(amt_min_key, WINDOW_SECONDS)

        # Event count for scoring trigger
        pipe.incr(self._key(employee_id, "event_count"))

        await pipe.execute()

    async def _get_float(self, key: str) -> float | None:
        v = await self._r.get(key)
        return float(v) if v is not None else None

    async def get_features(self, employee_id: str) -> dict[str, float]:
        """Retrieve aggregated features as a feature dict matching model feature names."""
        pipe = self._r.pipeline()
        scalar_keys = [
            "n", "sa", "sa2", "ngt", "s49", "s49_sum", "s45",
            "pass_count", "fail_count",
            "n_after_hours", "n_weekend", "records_sum",
            "mx", "amt_min", "bal_min", "bal_max", "bal_sum",
            "pr1k", "pr5k", "pr10k", "pr25k", "pr50k", "pxlg", "plrg",
        ]
        for k in scalar_keys:
            pipe.get(self._key(employee_id, k))
        hll_keys = ["nc_hll", "ncp_c_hll", "ncp_d_hll", "nch_hll", "nmcc_hll", "nip_hll"]
        for k in hll_keys:
            pipe.pfcount(self._key(employee_id, k))

        results = await pipe.execute()
        sv = {k: (float(results[i]) if results[i] is not None else 0.0)
              for i, k in enumerate(scalar_keys)}
        hv = {k: (float(results[len(scalar_keys) + i]) if results[len(scalar_keys) + i] else 0.0)
              for i, k in enumerate(hll_keys)}

        n = sv["n"] or 1.0
        nc = hv["nc_hll"]
        ncp_c = hv["ncp_c_hll"]
        ncp_d = hv["ncp_d_hll"]
        nch = hv["nch_hll"]
        nmcc = hv["nmcc_hll"]
        n_unique_ips = hv["nip_hll"]

        ngt = sv["ngt"]
        s49 = sv["s49"]
        pass_count = sv["pass_count"]
        fail_count = sv["fail_count"]
        n_after_hours = sv["n_after_hours"]
        n_weekend = sv["n_weekend"]
        sa = sv["sa"]
        sa2 = sv["sa2"]

        # Derived features
        mean_amt = sa / n
        std_amt = max(0.0, (sa2 / n - mean_amt ** 2) ** 0.5) if n > 1 else 0.0
        cv_amt = std_amt / mean_amt if mean_amt > 0 else 0.0
        pngt = ngt / n
        ps49 = s49 / n
        ps45 = sv["s45"] / n
        pass_rate = pass_count / (pass_count + fail_count) if (pass_count + fail_count) > 0 else 1.0
        fan_ratio = (ncp_c / ncp_d) if ncp_d > 0 else ncp_c
        fan_asymm = abs(ncp_c - ncp_d) / max(ncp_c + ncp_d, 1.0)
        hrs = n_after_hours / n      # after-hours transaction proportion → model feature 'hrs'
        pwkd = n_weekend / n         # weekend proportion → model feature 'pwkd'
        amt_range = sv["mx"] - sv["amt_min"] if sv["amt_min"] > 0 else sv["mx"]
        avg_records = sv["records_sum"] / n
        bal_mean = sv["bal_sum"] / n
        bal_cv = ((sv["bal_max"] - sv["bal_min"]) / bal_mean) if bal_mean > 0 else 0.0

        # Proportion features normalised by n
        pr1k = sv["pr1k"] / n
        pr5k = sv["pr5k"] / n
        pr10k = sv["pr10k"] / n
        pr25k = sv["pr25k"] / n
        pr50k = sv["pr50k"] / n
        pxlg = sv["pxlg"] / n
        plrg = sv["plrg"] / n

        return {
            # Per-employee transaction features (match model feat names)
            "n": sv["n"],
            "sa": sa,
            "mx": sv["mx"],
            "nc": nc,
            "ncp": nc,          # same concept
            "nch": nch,
            "nmcc": nmcc,
            "ngt": ngt,
            "s49": s49,
            "pngt": pngt,
            "ps49": ps49,
            "ps45": ps45,
            "pass_rate": pass_rate,
            "fan_ratio": fan_ratio,
            "fan_asymm": fan_asymm,
            "bal_min": sv["bal_min"],
            "bal_max": sv["bal_max"],
            "bal_mean": bal_mean,
            "bal_cv": bal_cv,
            "avg_balance": bal_mean,
            "mean_amt": mean_amt,
            "std_amt": std_amt,
            "cv_amt": cv_amt,
            "amt_range": amt_range,
            "hrs": hrs,          # after-hours proportion — important fraud signal
            "pwkd": pwkd,        # weekend proportion — important fraud signal
            "pr1k": pr1k,
            "pr5k": pr5k,
            "pr10k": pr10k,
            "pr25k": pr25k,
            "pr50k": pr50k,
            "pxlg": pxlg,
            "plrg": plrg,
            "ncp_c": ncp_c,
            "ncp_d": ncp_d,
            "n_unique_ips": n_unique_ips,
            "mule_ip_match": 0.0,
            "ip_mule_shared": 0.0,
            "ip_has_mule_ip": 0.0,
            "ip_mule_rate": 0.0,
        }

    async def get_event_count(self, employee_id: str) -> int:
        v = await self._r.get(self._key(employee_id, "event_count"))
        return int(v) if v else 0
