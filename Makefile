# MEZA — ATON+ internal AI operating system
# Native-process dev workflow (see docs/current-state.md for why: no Docker
# daemon in the audited environment). docker-compose.yml is kept in sync for
# hosts where Docker is available (e.g. the target Mac mini).

API_DIR := apps/api
WEB_DIR := apps/web
VENV := $(API_DIR)/.venv/bin

.PHONY: setup dev dev-api dev-web stop test migrate seed backup restore health ollama-pull lint

setup:
	cd $(API_DIR) && uv venv --python 3.12 .venv -q && uv pip install -q -e ".[dev]"
	cd $(WEB_DIR) && (command -v pnpm >/dev/null && pnpm install || npm install)
	@test -f .env || cp .env.example .env
	@echo "Setup complete. Edit .env, then run: make migrate seed dev"

migrate:
	cd $(API_DIR) && ../../$(VENV)/alembic upgrade head

seed:
	cd $(API_DIR) && ../../$(VENV)/meza create-admin
	cd $(API_DIR) && ../../$(VENV)/meza seed

dev-api:
	cd $(API_DIR) && .venv/bin/uvicorn meza.app:app --host 0.0.0.0 --port 8000 --reload

dev-web:
	cd $(WEB_DIR) && (command -v pnpm >/dev/null && pnpm dev || npm run dev)

dev:
	@echo "Starting API on :8000 and Web on :3000 (Ctrl+C stops both)"
	@trap 'kill 0' EXIT; $(MAKE) dev-api & $(MAKE) dev-web & wait

stop:
	@fuser -k 8000/tcp 2>/dev/null || true
	@fuser -k 3000/tcp 2>/dev/null || true
	@echo "Stopped MEZA API/Web (if running)."

test:
	cd $(API_DIR) && .venv/bin/pytest -q

lint:
	cd $(API_DIR) && .venv/bin/ruff check meza

backup:
	./scripts/backup.sh

restore:
	./scripts/restore.sh $(FILE)

health:
	@curl -s http://localhost:8000/api/v1/system/health | python3 -m json.tool || echo "API not reachable on :8000"

ollama-pull:
	ollama pull $(MODEL)
