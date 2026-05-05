# HAWKEYE — *Every Action Leaves a Trace*

> AI-powered real-time early-warning system that flags insider fraud by privileged bank employees **before** damage occurs.

Built by **NINEAGENTS** for the PSBs Hackathon Series 2026.  
Rank **#4 nationally** in RBI NFPC Phase 2 · AUC **0.998** · F1 **0.967** on 400M+ real banking transactions.

---

## Architecture

```
Synthetic Events (JSONL)
        │
        ▼
   Kafka Topic: hawkeye.events
        │
        ▼
   Stream Consumer (FastAPI background task)
   ├── Neo4j  — employee ↔ system ↔ resource graph
   └── Redis  — rolling window aggregates (30-day)
        │
        ▼
   Scoring Service
   ├── LightGBM M1 (clean features) + M2 (all features)
   ├── Blended score = w1·M1 + w2·M2
   └── SHAP TreeExplainer → top 5 factors
        │
        ▼
   Narrative Service (LangChain + Anthropic Claude)
        │
        ▼
   FastAPI REST + WebSocket API
        │
        ▼
   React + Vite + TypeScript Dashboard
```

Full diagram: [ARCHITECTURE.md](ARCHITECTURE.md)

---

## Quick Start (local)

> **Model files are not stored in git** (too large). They live on GitHub Releases and are downloaded by `make setup`.

```bash
# 1. Clone
git clone https://github.com/dhruvagrawal27/hawkeye.git
cd hawkeye

# 2. Download model artifacts + synthetic data (~50 MB, one-time)
#    Linux / Mac / Git-Bash:
bash scripts/download-artifacts.sh
#    Windows PowerShell:
#    .\scripts\download-artifacts.ps1

# 3. Configure environment
cp .env.example .env
# Open .env and set:  ANTHROPIC_API_KEY=sk-ant-...

# 4. Start everything
docker compose up --build
# First run takes 10-15 min (image pulls + builds).
# Wait for:  backend | INFO  Application startup complete

# 5. Seed DB + start live replay
make seed
make replay
```

Open **http://localhost:5173** → login: `analyst` / `analyst123`

## Demo

See [DEMO.md](DEMO.md) for the 5-minute judge demo script.

---

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for VPS runbook (Hetzner CX23, nginx, Let's Encrypt).

Live URL: **https://hawkeye.nineagents.in**

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy, Alembic |
| ML | LightGBM (pre-trained), SHAP TreeExplainer |
| LLM | Anthropic Claude via LangChain |
| Streaming | Apache Kafka (`confluent-kafka-python`) |
| Graph DB | Neo4j 5 Community |
| Cache | Redis 7 |
| RDBMS | Postgres 15 |
| Object Store | MinIO |
| Auth | Keycloak (JWT, roles: analyst / supervisor / admin) |
| Frontend | React 18, Vite, TypeScript, Tailwind CSS, shadcn/ui, D3.js |
| Observability | Prometheus + Grafana |
| ML Tracking | MLflow (sqlite backend) |
| Container | Docker + docker compose |

---

## Test Credentials

| User | Password | Role |
|------|----------|------|
| analyst@hawkeye.local | analyst | analyst |
| supervisor@hawkeye.local | supervisor | supervisor |

---

## What HAWKEYE Does NOT Do Yet (Future Work)

- **T-HGNN training**: Temporal Heterogeneous Graph Neural Network end-to-end training pipeline. Currently the LightGBM pipeline is the scoring engine; T-HGNN is on the roadmap.
- **Cross-bank federated learning**: Privacy-preserving model training across multiple institutions.
- **SimCLR contrastive pre-training**: Self-supervised contrastive learning for cold-start employee profiles.
- **Quantum-safe encryption**: Post-quantum cryptography for long-term data protection.
- **Voice / multimodal detection**: Audio and screen-capture anomaly signals.
- **HashiCorp Vault**: Secrets management. Current approach: `/opt/hawkeye/.env` with `chmod 600`.
- **mTLS between services**: Single-VPS deployment uses Docker internal network as trust boundary.
- **Air-gap deployment**: Offline / air-gapped bank-network deployment variant.
- **Multi-region failover**: HA active-active across datacentres.

---

## Team

**NINEAGENTS** — PSBs Hackathon Series 2026

---

## Licence

MIT — see [LICENSE](LICENSE)
