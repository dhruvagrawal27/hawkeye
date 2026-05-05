# HAWKEYE — VPS Deployment Runbook

Target: **Hetzner CX23** · 40 GB RAM · eu-central · IP `91.99.201.2`  
Domain: **hawkeye.nineagents.in** → `91.99.201.2`

---

## Pre-flight Checklist

- [ ] DNS A record: `hawkeye.nineagents.in → 91.99.201.2` (TTL 300)
- [ ] `dig hawkeye.nineagents.in` returns `91.99.201.2`
- [ ] `ssh root@91.99.201.2` works
- [ ] Inspect existing nginx: `systemctl status nginx`
- [ ] Existing `/ngo` project still responds: `curl -sI http://91.99.201.2/ngo`

---

## Step 1 — Bootstrap the VPS (one-time)

```bash
# From your laptop, copy the bootstrap script
scp deploy/bootstrap-vps.sh root@91.99.201.2:/tmp/
ssh root@91.99.201.2 'bash /tmp/bootstrap-vps.sh'
```

The script:
- Installs Docker CE + docker compose plugin (if missing)
- Installs certbot + python3-certbot-nginx
- Creates `/opt/hawkeye/` and `/opt/hawkeye-data/` with correct permissions
- Creates `hawkeye` Linux user in the `docker` group
- Opens UFW ports 22, 80, 443 (if UFW is active)

---

## Step 2 — Upload Artifacts (one-time)

```bash
# Model artifacts
rsync -avz --progress \
  lgb_model_m1_full.txt lgb_model_m2_full.txt \
  feature_config.json feature_stats.json \
  account_feature_matrix.parquet oof_predictions.parquet \
  train_metadata.json \
  root@91.99.201.2:/opt/hawkeye-data/artifacts/

# Synthetic data
rsync -avz --progress \
  synthetic_events.jsonl synthesis_metadata.json \
  synthetic_accounts.parquet synthetic_transactions.parquet \
  synthetic_labels.parquet \
  root@91.99.201.2:/opt/hawkeye-data/synthetic/
```

---

## Step 3 — Clone Repo and Configure

```bash
ssh root@91.99.201.2
cd /opt
git clone https://github.com/nineagents/hawkeye-nineagents.git hawkeye
cd hawkeye
cp .env.example .env
chmod 600 .env
nano .env   # set ANTHROPIC_API_KEY and any other secrets
```

---

## Step 4 — Install nginx Server Block

```bash
# On the VPS
sudo cp /opt/hawkeye/infra/nginx/hawkeye.nineagents.in.conf \
        /etc/nginx/sites-available/hawkeye.nineagents.in
sudo ln -s /etc/nginx/sites-available/hawkeye.nineagents.in \
           /etc/nginx/sites-enabled/hawkeye.nineagents.in
sudo nginx -t
sudo systemctl reload nginx
```

**Do not touch** any other file in `/etc/nginx/sites-enabled/`. The existing `/ngo`
project is served by a different `server_name` and will continue working unchanged.

---

## Step 5 — Issue TLS Certificate

```bash
sudo certbot --nginx \
  -d hawkeye.nineagents.in \
  --email your@email.com \
  --agree-tos \
  --no-eff-email

# Verify auto-renewal
sudo certbot renew --dry-run
```

---

## Step 6 — Initial Deploy

```bash
cd /opt/hawkeye
bash deploy/deploy.sh
```

Expected output ends with:
```
Deploy complete.
/ngo OK
/ngo/dashboard OK
```

---

## Step 7 — Verify

```bash
# HAWKEYE health
curl -sf https://hawkeye.nineagents.in/api/healthz | python3 -m json.tool

# TLS cert
echo | openssl s_client -connect hawkeye.nineagents.in:443 -servername hawkeye.nineagents.in 2>&1 | grep -E 'subject|expire'

# Coexistence check
curl -sI http://91.99.201.2/ngo
curl -sI http://91.99.201.2/ngo/dashboard
```

---

## Persistent Data Layout

```
/opt/hawkeye-data/
├── postgres/           # PostgreSQL data directory
├── neo4j/
│   ├── data/           # Neo4j database files
│   └── logs/
├── kafka/data/         # Kafka log segments
├── redis/data/         # Redis RDB/AOF
├── minio/data/         # MinIO object store
├── keycloak/data/      # Keycloak H2 / import state
├── mlflow/             # MLflow sqlite + mlruns
├── grafana/            # Grafana dashboards + datasources
├── artifacts/          # LightGBM models + config (upload once)
└── synthetic/          # synthetic_events.jsonl + parquets (upload once)
```

**`docker compose down -v` will NOT wipe this data** — it lives in bind mounts outside
the Docker named volumes. Safe to rebuild containers without losing state.

---

## SSH Tunnel Access (Internal Admin UIs)

These services are **NOT** publicly exposed in production. Access via SSH tunnel:

```bash
# Grafana (metrics dashboards)
ssh -L 3001:localhost:3001 root@91.99.201.2
# → http://localhost:3001  (admin / admin, change on first login)

# Neo4j Browser (graph exploration)
ssh -L 7474:localhost:7474 -L 7687:localhost:7687 root@91.99.201.2
# → http://localhost:7474  (neo4j / <NEO4J_PASSWORD from .env>)

# MLflow (model registry)
ssh -L 5000:localhost:5000 root@91.99.201.2
# → http://localhost:5000

# MinIO Console (artifact storage)
ssh -L 9001:localhost:9001 root@91.99.201.2
# → http://localhost:9001  (minioadmin / <MINIO_ROOT_PASSWORD from .env>)

# Prometheus (raw metrics)
ssh -L 9090:localhost:9090 root@91.99.201.2
# → http://localhost:9090

# Keycloak Admin
ssh -L 8081:localhost:8081 root@91.99.201.2
# → http://localhost:8081/admin  (admin / <KEYCLOAK_ADMIN_PASSWORD from .env>)
```

---

## GitHub Actions Continuous Deployment

Required GitHub Secrets (Settings → Secrets → Actions):

| Secret | Value |
|--------|-------|
| `VPS_HOST` | `91.99.201.2` |
| `VPS_USER` | `root` (or `hawkeye`) |
| `VPS_SSH_KEY` | private key (ed25519) |

Generate deploy key:
```bash
ssh-keygen -t ed25519 -C "github-actions-hawkeye" -f ~/.ssh/hawkeye_deploy
# Add ~/.ssh/hawkeye_deploy.pub to /root/.ssh/authorized_keys on the VPS
# Add ~/.ssh/hawkeye_deploy (private) as VPS_SSH_KEY secret in GitHub
```

Every push to `main` triggers `.github/workflows/deploy.yml` → SSH → `deploy.sh` →
live site updates within 5 minutes, downtime < 30s (rolling container restart).

---

## Coexistence with Existing `/ngo` Project

The existing project at `http://91.99.201.2/ngo` uses the host's **default nginx server
block** (matched by IP, no `server_name`). HAWKEYE uses `server_name hawkeye.nineagents.in`.
nginx routes by Host header; they never collide.

**Verification** (run after every deploy):
```bash
curl -sfI http://127.0.0.1/ngo           # must return 200 or 301
curl -sfI http://127.0.0.1/ngo/dashboard # must return 200 or 301
```

If either returns an error, **do not proceed** — the nginx config has a conflict.
Run `sudo nginx -t` and check `/var/log/nginx/error.log`.

---

## Rollback

```bash
ssh root@91.99.201.2
cd /opt/hawkeye
git log --oneline -10
git reset --hard <previous-commit-sha>
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```
