#!/usr/bin/env bash
# Idempotent deploy script — runs on the VPS
set -euo pipefail

REPO_DIR=/opt/hawkeye
DATA_DIR=/opt/hawkeye-data
COMPOSE="docker compose -f $REPO_DIR/docker-compose.yml -f $REPO_DIR/docker-compose.prod.yml"

cd "$REPO_DIR"

echo "==> Pulling latest code..."
git fetch --all --prune
git reset --hard origin/main

echo "==> Ensuring data directories exist..."
mkdir -p "$DATA_DIR"/{postgres,neo4j/data,neo4j/logs,kafka/data,redis/data,minio/data,keycloak/data,mlflow,grafana,artifacts,synthetic}

echo "==> Symlinking data dirs into repo..."
ln -sfn "$DATA_DIR/artifacts" backend/artifacts
ln -sfn "$DATA_DIR/synthetic" backend/data

echo "==> Building and starting services..."
$COMPOSE pull --quiet
$COMPOSE build --quiet
$COMPOSE up -d --remove-orphans

echo "==> Waiting for backend to be healthy..."
HEALTHY=false
for i in $(seq 1 60); do
    if curl -sf http://127.0.0.1:8000/healthz >/dev/null 2>&1; then
        HEALTHY=true
        echo "Backend healthy after ${i}x2s."
        break
    fi
    sleep 2
done

if [ "$HEALTHY" != "true" ]; then
    echo "ERROR: Backend did not become healthy in 120s"
    $COMPOSE logs --tail=50 backend
    exit 1
fi

echo "==> Running database migrations..."
$COMPOSE exec -T backend alembic upgrade head

echo "==> Running seed (idempotent)..."
$COMPOSE exec -T backend python -m app.scripts.seed_if_empty

echo "==> Verifying /ngo coexistence..."
curl -sfI http://127.0.0.1/ngo > /dev/null && echo "/ngo OK" || echo "WARNING: /ngo may be broken — check nginx config"
curl -sfI http://127.0.0.1/ngo/dashboard > /dev/null && echo "/ngo/dashboard OK" || echo "WARNING: /ngo/dashboard may be broken — check nginx config"

echo ""
echo "==> Deploy complete! https://hawkeye.nineagents.in"
