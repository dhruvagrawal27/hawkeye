"""LangChain + Anthropic narrative generation service."""

from __future__ import annotations

import structlog
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.models import Alert, Narrative

log = structlog.get_logger()
settings = get_settings()

_CANNED_NARRATIVE = """
**Risk Summary:** This employee has been flagged as HIGH risk based on anomalous transaction patterns.

**What We Observed:** Multiple statistical indicators deviated significantly from peer baselines, including elevated pass-through rates and structured transaction amounts.

**Why It Matters:** These patterns are consistent with known insider fraud and money-mule activity detected in our AML pipeline.

**Recommended Next Step:** Initiate a formal review with the compliance team within 24 hours and temporarily restrict data-export privileges pending investigation.

---
*Note: LLM narrative generation was unavailable. This is a pre-canned fallback.*
"""

_SEVERITY_MAP = {
    "low": "LOW", "medium": "MEDIUM", "high": "HIGH", "critical": "CRITICAL"
}


def _load_prompt_template() -> str:
    p = Path(__file__).parent.parent / "prompts" / "investigation_narrative.md"
    if p.exists():
        return p.read_text()
    return """
You are a senior bank fraud investigator. Generate a structured investigation narrative for the following insider threat alert.

Alert data:
- Employee: {employee_id}
- Risk Score: {score:.3f} (threshold: {threshold:.3f})
- Severity: {severity}
- Top Risk Factors:
{factors_text}

Format your response with EXACTLY these four sections:
## Risk Summary
One sentence. State the severity and the most prominent signal.

## What We Observed
Describe the concrete behaviours, citing feature names in plain English.

## Why It Matters
Link to known fraud patterns (structuring, mule activity, data exfiltration).

## Recommended Next Step
One specific, actionable recommendation.

---
**SHAP Attribution (audit trail):**
{shap_footer}
"""


class NarrativeService:
    def __init__(self) -> None:
        self._llm = None
        self._model_version = settings.anthropic_model

    def _get_llm(self):
        if self._llm is not None:
            return self._llm
        try:
            from langchain_anthropic import ChatAnthropic
            self._llm = ChatAnthropic(
                model=settings.anthropic_model,
                api_key=settings.anthropic_api_key,
                timeout=30,
                max_retries=0,  # tenacity handles retries
            )
            return self._llm
        except Exception as exc:
            log.warning("llm_init_failed", error=str(exc))
            return None

    def _build_prompt(self, alert: Alert) -> str:
        factors = alert.risk_factors or []
        factors_text = "\n".join(
            f"  - {f.get('plain_name', f.get('feature', '?'))}: {f.get('contribution', 0):+.4f}"
            for f in factors
        )
        shap_footer = "\n".join(
            f"{f.get('feature', '?')}: {f.get('contribution', 0):+.4f}"
            for f in factors
        )
        template = _load_prompt_template()
        return template.format(
            employee_id=alert.employee_id,
            score=alert.score,
            threshold=alert.threshold,
            severity=alert.severity.upper(),
            factors_text=factors_text or "  - No SHAP data available",
            shap_footer=shap_footer or "No SHAP data available",
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def _call_llm(self, prompt: str) -> tuple[str, dict]:
        llm = self._get_llm()
        if llm is None:
            raise RuntimeError("LLM not available")
        from langchain_core.messages import HumanMessage
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        token_usage = {}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            token_usage = {
                "input": response.usage_metadata.get("input_tokens", 0),
                "output": response.usage_metadata.get("output_tokens", 0),
            }
        return response.content, token_usage

    async def generate(self, alert: Alert, db: AsyncSession, force: bool = False) -> Narrative:
        prompt = self._build_prompt(alert)
        shap_footer_lines = [
            f"{f.get('feature', '?')}: {f.get('contribution', 0):+.4f}"
            for f in (alert.risk_factors or [])
        ]
        shap_footer = "\n".join(shap_footer_lines)
        content = _CANNED_NARRATIVE
        token_usage: dict = {}

        try:
            content, token_usage = await self._call_llm(prompt)
        except Exception as exc:
            log.warning("narrative_llm_failed", alert_id=str(alert.id), error=str(exc))
            content = _CANNED_NARRATIVE

        # Append SHAP footer if not already present
        if shap_footer and "SHAP Attribution" not in content:
            content += f"\n\n---\n**SHAP Attribution (audit trail):**\n{shap_footer}"

        narrative = Narrative(
            alert_id=alert.id,
            model_version=self._model_version,
            content=content,
            shap_footer=shap_footer,
            token_usage=token_usage,
        )
        db.add(narrative)
        await db.commit()
        await db.refresh(narrative)
        log.info("narrative_generated", alert_id=str(alert.id), tokens=token_usage)
        return narrative
