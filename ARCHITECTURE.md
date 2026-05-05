# HAWKEYE — Architecture

## System Diagram

```
                          ┌──────────────────────────────────┐
   Replay producer  ───►  │   Kafka topic: hawkeye.events    │
   (jsonl → stream)       └────────────────┬─────────────────┘
                                           │
                                           ▼
                          ┌──────────────────────────────────┐
                          │   Stream consumer (FastAPI bg    │
                          │   task / confluent-kafka-python) │
                          └──┬───────────────────────────┬───┘
                             │                           │
                             ▼                           ▼
        ┌─────────────────────────┐    ┌────────────────────────────────────┐
        │ Feature aggregator       │    │ Neo4j graph (employee → system →   │
        │ (Redis rolling windows:  │    │ resource); maintained live         │
        │ pass_rate, pngt, ps49,   │    └────────────────────┬───────────────┘
        │ fan_ratio, etc.)         │                         │
        └────────────┬─────────────┘                         │
                     │                                       │
                     ▼                                       ▼
        ┌──────────────────────────────────────────────────────────────────┐
        │ Scoring service                                                   │
        │  • Loads lgb_model_m1_full.txt + lgb_model_m2_full.txt            │
        │  • Reads aggregated features from Redis + graph features Neo4j    │
        │  • blended = w1·M1 + w2·M2  (weights from feature_config.json)   │
        │  • SHAP TreeExplainer on M2 → top 5 contributing features        │
        │  • Writes RiskScore + RiskFactors to Postgres                    │
        └────────────┬─────────────────────────────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────────────────────────────────┐
        │ Narrative service (LangChain + Anthropic Claude)                  │
        │  Triggered when score ≥ threshold; writes Narrative to Postgres   │
        └────────────┬─────────────────────────────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────────────────────────────────┐
        │ FastAPI public API:  /alerts /employees/{id} /graph/{id}         │
        │                       /narrative/{alert_id} /events/replay       │
        │                       /ws/alerts (WebSocket)                     │
        └────────────┬─────────────────────────────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────────────────────────────────┐
        │ React + Vite + TS dashboard (Tailwind + shadcn/ui + D3.js)       │
        └──────────────────────────────────────────────────────────────────┘

   Cross-cutting:
   • Postgres 15   — alerts, narratives, triage history, audit log
   • Redis 7       — rolling window state, hot cache for active sessions
   • MinIO         — model artifact storage (S3-compatible)
   • MLflow        — model registry + experiment tracking (sqlite backend)
   • Prometheus + Grafana — service metrics (SSH-tunnel access only in prod)
   • Keycloak      — single realm "hawkeye", roles: analyst, supervisor, admin
```

## Component Descriptions

### Kafka Topic: `hawkeye.events`
Single partition topic receiving all synthetic events. Each event is a JSON object with
dual schema: banking fields + insider-threat overlay fields. The producer replays
`synthetic_events.jsonl` at a configurable rate (default 50 ev/s).

### Stream Consumer
Runs as a FastAPI background task using `confluent-kafka-python`. Processes each event:
1. Updates Neo4j graph (MERGE employee → accessed → system resource)
2. Updates Redis rolling-window aggregates per employee
3. Every N events (default 10) or 60s, triggers scoring for that employee
4. On score ≥ threshold: writes Alert to Postgres (deduplicated within 1-hour window)

### Scoring Service
- Loads both LightGBM boosters at startup (once, never reloaded)
- Feature vector built from Redis aggregates + graph features
- Missing features imputed with per-feature p50 from `feature_stats.json`
- Inputs clipped to `[min, max]` from feature stats
- SHAP background dataset: 200-row sample, cached at startup
- Returns: blended score, M1, M2, top-5 SHAP factors (signed)

### Narrative Service
- LangChain `ChatAnthropic` with `claude-sonnet-4-5` (configurable)
- 30s timeout, max 3 retries, falls back to pre-canned narrative
- Narratives cached in Postgres keyed by `(alert_id, model_version)`
- Every narrative ends with SHAP factors verbatim (auditability)

### Neo4j Graph
- Nodes: Employee, SystemResource
- Edges: ACCESSED (timestamp, amount, access_type)
- Seeded on startup from synthetic data if graph is empty
- Used for collusion-ring detection: shared resource overlap between flagged employees

### Frontend
- React 18 + Vite + TypeScript + Tailwind CSS + shadcn/ui
- `keycloak-js` for OIDC authentication; JWT attached to all API requests
- WebSocket subscription to `/ws/alerts` for live alert push
- D3.js force-directed graph for employee-resource topology

## Data Flow: Insider-Threat Overlay

The LightGBM model was trained on banking features (`account_id`, `amount`, `txn_type`, etc.).
The dashboard speaks insider-threat (`employee_id`, `system_resource`, `access_type`).
The mapping is 1-to-1 and deterministic:

```
account_id      ↔  employee_id
counterparty_id ↔  system_resource
amount          ↔  records_accessed (scaled)
txn_type        ↔  access_type
is_after_hours  ↔  is_after_hours (direct)
is_weekend      ↔  is_weekend (direct)
```

This translation happens in the API layer before any response is returned to the frontend.

## Port Map (Development)

| Service | Port |
|---------|------|
| Frontend | 8080 |
| Backend API | 8000 |
| Keycloak | 8081 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| Neo4j Browser | 7474 |
| Neo4j Bolt | 7687 |
| Kafka | 9092 |
| MinIO Console | 9001 |
| MLflow | 5000 |
| Prometheus | 9090 |
| Grafana | 3001 |

In production (`docker-compose.prod.yml`), all admin ports are bound to `127.0.0.1` only.
