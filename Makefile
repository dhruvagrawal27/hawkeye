.PHONY: up down seed replay test fmt lint deploy logs ps setup

# ── First-time setup ──────────────────────────────────────────────────────
## Download model artifacts from GitHub Releases (run once after git clone)
setup:
	@echo "Downloading model artifacts & synthetic data..."
	@bash scripts/download-artifacts.sh

# ── Local dev ─────────────────────────────────────────────────────────────
up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f backend

ps:
	docker compose ps

# ── Data & models ─────────────────────────────────────────────────────────
seed:
	docker compose exec backend python -m app.scripts.seed_if_empty

replay:
	curl -sf -X POST http://localhost:8000/events/replay \
	     -H "Content-Type: application/json" \
	     -d '{"action":"start","rate":200}' | python3 -m json.tool

replay-stop:
	curl -sf -X POST http://localhost:8000/events/replay \
	     -H "Content-Type: application/json" \
	     -d '{"action":"stop"}' | python3 -m json.tool

# ── Quality ───────────────────────────────────────────────────────────────
test:
	docker compose exec backend pytest tests/ -v
	cd frontend && npm run test

fmt:
	docker compose exec backend ruff format app/
	cd frontend && npm run format

lint:
	docker compose exec backend ruff check app/
	docker compose exec backend mypy app/
	cd frontend && npm run lint

# ── Production deploy ─────────────────────────────────────────────────────
deploy:
	ssh root@91.99.201.2 'bash /opt/hawkeye/deploy/deploy.sh'

# ── Helpers ───────────────────────────────────────────────────────────────
wait:
	bash deploy/wait-for-stack.sh

migrate:
	docker compose exec backend alembic upgrade head

shell-backend:
	docker compose exec backend bash

shell-db:
	docker compose exec postgres psql -U hawkeye -d hawkeye
