# HAWKEYE — 5-Minute Demo Script

> Timed for a judge walk-through. Presenter notes in *italics*.

---

## Setup (before judges arrive)

1. SSH tunnel for Grafana: `ssh -L 3001:localhost:3001 root@91.99.201.2`
2. Open `https://hawkeye.nineagents.in` in Chrome, **not logged in yet**.
3. Ensure replay is stopped (`GET /api/events/replay/status` → `running: false`).

---

## 0:00 — Opening

> *Open the browser. Show the Keycloak login page.*

"We're looking at HAWKEYE — *Every Action Leaves a Trace* — an AI early-warning system
that flags insider fraud by privileged bank employees before damage occurs."

Log in as `analyst@hawkeye.local` / `analyst`.

> *Dashboard loads. Alert feed is empty. Counters show zero.*

"Right now we're monitoring a synthetic cohort representing 10,000 privileged bank
employees. No events have been processed yet. The graph on the right shows the static
access topology — who has keys to which systems."

---

## 0:30 — Start Replay

> *Click the **Start Replay** button in the header. Set rate to 200 events/sec.*

"Each event is drawn from our synthetic insider-threat dataset generated using the same
statistical signatures that scored AUC 0.998 on 400 million real banking transactions."

> *Watch the live counters tick: Events Processed, Employees Scored, Alerts.*

"Under the hood: every event lands in Kafka, our consumer updates a Neo4j graph and
Redis rolling-window aggregates, then every 10 events per employee we trigger a blended
LightGBM score — two models, weights from our trained pipeline."

---

## 1:30 — First Alert

> *A red alert card appears in the feed. Click it.*

"Here's our first high-risk flag. Employee ID `EMP-0042`. Risk score **0.91** — well above
our calibrated threshold of **0.42**."

> *The SHAP waterfall chart renders on the right panel.*

"Let's see *why* the model fired. Top factors:

- **pass_rate** — this employee's transaction pass-through rate is 3.4 standard deviations
  above baseline. Classic structuring behaviour.
- **ps49** — 6 transactions just below the ₹49,999 reporting threshold in the last 30 days.
- **pngt** — negative-transaction ratio is elevated: reversals happening faster than deposits.
- **g_mcs** — graph centrality: this employee sits at a hub in the access graph.

These are the same statistical signatures that our AML mule-detection pipeline catches
in real banking data — we've just re-projected them onto the insider-threat axis."

---

## 2:30 — Generate Narrative

> *Click **Generate Narrative** button on the alert detail panel.*

> *Wait 3–5 seconds while Claude generates. The panel fills with text.*

"Our LLM layer — Anthropic Claude — writes a structured investigation memo from those
SHAP signals."

> *Read the **Recommended next step** section aloud:*

"Recommended: *Freeze EMP-0042's data-export privileges pending a 48-hour transaction
review by a supervisor. Cross-reference with the HR calendar for any upcoming
resignation or performance-review dates.*"

"Notice the footer: every narrative lists the raw SHAP values — feature name, signed
contribution. That's our auditability hook for FREE-AI compliance. A regulator can
trace exactly which signal drove the flag."

---

## 3:30 — Graph View

> *Click the **Graph** tab on the employee detail page.*

"Now look at the access topology. EMP-0042 — shown in red — shares **3 system resources**
with two other employees who are also in the alert queue: EMP-0017 and EMP-0089.
That's a collusion-ring signature that a flat model misses entirely because it only
looks at individual behaviour."

> *Hover over a shared node — the tooltip shows the system name and access count.*

"This graph is maintained live by our Neo4j service. Every event updates the edges
in real time."

---

## 4:00 — (Optional) Grafana Metrics

> *Switch to the pre-opened Grafana tab (localhost:3001 via SSH tunnel).*

"Under load — 200 events per second — end-to-end scoring latency sits at **p95 < 180ms**.
85% of legitimate synthetic traffic is correctly ignored. The alert rate is less than
2% of employees flagged per hour, calibrated to minimise analyst fatigue."

---

## 4:30 — Close

"From **77 days** — the industry average detection lag for insider fraud — to **under
1 second**. At Union Bank scale, that's an estimated **₹100–500 crore per year** saved
in prevented fraud losses."

"HAWKEYE is production-ready: one `docker compose up`, Let's Encrypt TLS, Keycloak
auth, full observability. Built on a pipeline already battle-tested at Rank #4
nationally in the RBI NFPC challenge."

"Thank you."

---

## Backup Talking Points

- **Why not train a graph neural network from scratch?**
  T-HGNN is on the roadmap. Today's LightGBM pipeline is already superhuman on the
  AML benchmark. We ship a working product, not a research prototype.
- **Where does the synthetic data come from?**
  Generated from the statistical distributions of real AML data using a privacy-safe
  synthesis pipeline. Same feature space, no real PII.
- **How does Keycloak integrate?**
  Standard OIDC flow. JWT roles (`analyst`, `supervisor`, `admin`) gate every API
  endpoint. Supervisors can trigger narrative regeneration; analysts can only read.
