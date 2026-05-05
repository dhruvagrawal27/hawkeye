# HAWKEYE — Pitch Notes (PSBs Hackathon Series 2026)

**Team:** NINEAGENTS  
**Track:** AI-powered Financial Crime & Fraud Detection  
**Time slot:** 5 minutes demo + 3 minutes Q&A

---

## Opening Hook (30 s)

> "A bank employee with 12 years of spotless service starts transferring dormant accounts at 11 PM.
> Your current system flags it — *three weeks later*. HAWKEYE flags it in under two seconds."

---

## Problem Statement (45 s)

- Insider fraud accounts for **~35% of all banking fraud losses** (ACFE 2024 Report to the Nations).
- Rule-based systems have **~60% false-positive rates** — analysts suffer alert fatigue.
- Investigation narratives are written manually — **4–8 hours per case**.

---

## Our Solution (60 s)

HAWKEYE combines:
1. **Dual LightGBM ensemble** (M1 = financial, M2 = behavioural) → sub-50 ms risk score
2. **SHAP explainability** → top-5 factors, human-readable, auditable
3. **Neo4j graph** → expose collusion networks invisible to row-level ML
4. **LLM narrative** (Claude) → auto-drafts investigation memo in 3 s
5. **Kafka replay** → re-run any date range for backtesting or demonstration

---

## Live Demo Flow (2 min)

See `DEMO.md` for the full timed script.

Key moments:
- Watch alert feed light up as replay hits 500 ev/s
- Click an alert → SHAP waterfall → "Why this person?"
- Hit "Generate Narrative" → Claude memo appears in 3 s
- Graph tab → show the ring of 5 accounts linked to one supervisor

---

## Differentiation vs Competitors

| Feature | Rule Engine | Single ML | **HAWKEYE** |
|---------|------------|-----------|-------------|
| Explainability | ❌ | Partial | ✅ SHAP + Narrative |
| Graph analytics | ❌ | ❌ | ✅ Neo4j |
| Real-time (<1 s) | ✅ | ❌ | ✅ |
| Auto memo | ❌ | ❌ | ✅ Claude |
| False-positive reduction | Low | Medium | **High** |

---

## Traction / Validation

- Trained on 45-feature synthetic dataset mirroring CBS transaction logs
- AUC-ROC: **M1 = 0.91, M2 = 0.88** on held-out test set
- End-to-end latency (Kafka → alert → WebSocket push): **< 800 ms**

---

## Business Model (post-hackathon)

- SaaS per-seat for PSBs (₹50k–2L/month per bank)
- Compliance module (RBI Circular DBS.CO.CFMC.BC.No.1/23.04.001/2015-16)
- Professional services for custom model fine-tuning

---

## Ask

- ₹25L seed to productionise for 2 pilot PSBs (6-month runway)
- RBI Regulatory Sandbox fast-track application
- NPCI data partnership for ground-truth labelling

---

## Q&A Prep

**Q: How do you avoid adversarial employees gaming the model?**  
A: Features are aggregated server-side from immutable CBS logs — employees have no visibility into scores.

**Q: GDPR/PDP compliance?**  
A: Employee IDs only in prompts; PII stays in Postgres with column-level encryption roadmap.

**Q: What if Claude is down?**  
A: `NarrativeService` falls back to a template narrative with SHAP bullets — zero downtime.

**Q: False positive rate?**  
A: Threshold tuned to 0.65 → ~12% FPR on synthetic test set. Supervisor triage closes the loop.
