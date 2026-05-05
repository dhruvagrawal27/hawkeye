"""LightGBM scoring service."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import numpy as np
import structlog

log = structlog.get_logger()

# Lazy imports to avoid ImportError at module load when running tests without all deps
try:
    import lightgbm as lgb
    import shap
    HAS_LGB = True
except ImportError:
    HAS_LGB = False

_PLAIN_NAMES: dict[str, str] = {
    "pass_rate": "Transaction pass-through rate",
    "pngt": "Negative-transaction ratio",
    "ps49": "Sub-49K structuring count",
    "fan_ratio": "Fan-out to fan-in ratio",
    "g_mcs": "Graph max connected-component size",
    "n": "Total transaction count",
    "sa": "Sum of amounts",
    "nc": "Unique counterparties",
    "ngt": "Negative transaction count",
    "s49": "Sum of sub-49K transactions",
    "bal_min": "Minimum balance",
    "ncp_c": "Unique credit counterparties",
    "ncp_d": "Unique debit counterparties",
    "mule_ip_match": "Mule IP flag",
}


class ScoringService:
    def __init__(self) -> None:
        self.loaded = False
        self._m1: Any = None
        self._m2: Any = None
        self._feat_cols: list[str] = []
        self._feat_clean: list[str] = []
        self._w1: float = 0.5
        self._w2: float = 0.5
        self._threshold: float = 0.5
        self._stats: dict[str, dict] = {}
        self._shap_explainer: Any = None
        self._shap_bg: np.ndarray | None = None

    async def load(self) -> None:
        await asyncio.get_event_loop().run_in_executor(None, self._load_sync)

    def _load_sync(self) -> None:
        from app.config import get_settings
        settings = get_settings()

        if not HAS_LGB:
            log.warning("lightgbm_not_installed")
            return

        m1_path = Path(settings.model_m1_path)
        m2_path = Path(settings.model_m2_path)
        cfg_path = Path(settings.feature_config_path)
        stats_path = Path(settings.feature_stats_path)

        if not m1_path.exists() or not m2_path.exists():
            log.warning("model_files_missing", m1=str(m1_path), m2=str(m2_path))
            return

        self._m1 = lgb.Booster(model_file=str(m1_path))
        self._m2 = lgb.Booster(model_file=str(m2_path))
        log.info("models_loaded")

        if cfg_path.exists():
            with open(cfg_path) as f:
                cfg = json.load(f)
            self._feat_cols = cfg.get("feat_cols", [])
            self._feat_clean = cfg.get("feat_clean", [])
            blend = cfg.get("blend_weights", {})
            self._w1 = blend.get("w1", 0.5)
            self._w2 = blend.get("w2", 0.5)
            self._threshold = cfg.get("threshold", 0.5)
            log.info("feature_config_loaded", feats=len(self._feat_cols), threshold=self._threshold)

        if stats_path.exists():
            with open(stats_path) as f:
                self._stats = json.load(f)
            log.info("feature_stats_loaded", features=len(self._stats))

        # Build SHAP background dataset from stats medians
        if self._feat_cols and self._stats:
            bg = np.array([
                [self._stats.get(c, {}).get("p50", 0.0) for c in self._feat_cols]
            ] * min(settings.shap_background_rows, 200))
            self._shap_explainer = shap.TreeExplainer(self._m2, bg)
            log.info("shap_explainer_ready")

        self.loaded = True

    def _build_vector(self, features: dict[str, Any], feat_list: list[str]) -> np.ndarray:
        vec = []
        for col in feat_list:
            val = features.get(col)
            if val is None:
                val = self._stats.get(col, {}).get("p50", 0.0)
            # Clip
            col_stats = self._stats.get(col, {})
            if col_stats:
                val = float(np.clip(val, col_stats.get("min", val), col_stats.get("max", val)))
            vec.append(float(val) if val is not None else 0.0)
        return np.array(vec, dtype=np.float64)

    def score(self, features: dict[str, Any]) -> dict[str, Any]:
        if not self.loaded or not HAS_LGB:
            return {
                "score": 0.0, "m1": 0.0, "m2": 0.0,
                "top_factors": [], "threshold": self._threshold, "is_alert": False,
            }

        vec_full = self._build_vector(features, self._feat_cols).reshape(1, -1)
        m2 = float(self._m2.predict(vec_full)[0])

        vec_clean = self._build_vector(features, self._feat_clean).reshape(1, -1)
        m1 = float(self._m1.predict(vec_clean)[0])

        blended = self._w1 * m1 + self._w2 * m2

        # SHAP
        top_factors = []
        if self._shap_explainer is not None:
            try:
                shap_vals = self._shap_explainer.shap_values(vec_full)[0]
                indices = np.argsort(np.abs(shap_vals))[::-1][:5]
                for i in indices:
                    fname = self._feat_cols[i]
                    top_factors.append({
                        "feature": fname,
                        "contribution": float(shap_vals[i]),
                        "plain_name": _PLAIN_NAMES.get(fname, fname),
                    })
            except Exception as exc:
                log.warning("shap_failed", error=str(exc))

        return {
            "score": blended,
            "m1": m1,
            "m2": m2,
            "top_factors": top_factors,
            "threshold": self._threshold,
            "is_alert": blended >= self._threshold,
        }

    @property
    def threshold(self) -> float:
        return self._threshold
