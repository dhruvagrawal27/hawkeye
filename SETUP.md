# Setup Guide — New Machine / Fresh Clone

## Why are `backend/artifacts/` and `backend/data/` empty?

Model files (`.txt`) and data files (`.jsonl`, `.parquet`) are **never stored in git** because:
- They are large binary files (model files ~3 MB each, synthetic data ~150 MB)
- They should not be version-controlled with code

They are hosted on **GitHub Releases** and downloaded separately.

---

## Step 1 — Download artifacts (one-time)

### Windows (PowerShell)
```powershell
cd path\to\hawkeye
.\scripts\download-artifacts.ps1
```

### Linux / Mac / Git Bash
```bash
cd path/to/hawkeye
bash scripts/download-artifacts.sh
```

### Or with Make (Linux/Mac)
```bash
make setup
```

This downloads these 5 files from the [v1.0.0 GitHub Release](https://github.com/dhruvagrawal27/hawkeye/releases/tag/v1.0.0):

| File | Destination | Purpose |
|------|-------------|---------|
| `lgb_model_m1_full.txt` | `backend/artifacts/` | LightGBM model #1 (financial features) |
| `lgb_model_m2_full.txt` | `backend/artifacts/` | LightGBM model #2 (behavioural features) |
| `feature_config.json` | `backend/artifacts/` | Feature list + blend weights + threshold |
| `feature_stats.json` | `backend/artifacts/` | Feature statistics for imputation |
| `synthetic_events.jsonl` | `backend/data/` | 516,650 synthetic bank transactions for Kafka replay |

---

## Step 2 — Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:
```
ANTHROPIC_API_KEY=sk-ant-...your key here...
```

All other defaults work for local development.

---

## Step 3 — Start the stack

```bash
docker compose up --build
```

First run: **10–15 minutes** (image downloads + builds).  
Subsequent runs: **~30 seconds**.

**Ready when you see:**
```
backend    | INFO  models_loaded
backend    | INFO  shap_explainer_ready  
backend    | INFO  Application startup complete
```

---

## Step 4 — Open the app

| Service | URL | Credentials |
|---------|-----|-------------|
| Dashboard | http://localhost:5173 | analyst / analyst123 |
| API Docs | http://localhost:8000/docs | — |
| Grafana | http://localhost:3000 | admin / changeme_grafana |
| Keycloak Admin | http://localhost:8080 | admin / changeme_keycloak |

---

## Step 5 — Start the fraud demo

```bash
make seed     # seed database + graph
make replay   # start Kafka replay at 200 ev/s
```

Or click **Start Replay** in the dashboard UI.

---

## Troubleshooting

**"model_files_missing" in backend logs**  
→ You skipped Step 1. Run `.\scripts\download-artifacts.ps1` then restart: `docker compose restart backend`

**Keycloak takes forever to start**  
→ Normal on first boot (importing realm). Wait 2–3 min or run `docker compose logs keycloak -f`

**Port already in use**  
→ Another service is using a port. Check `docker compose ps` and stop conflicting containers.
