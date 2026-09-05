# Deployment

## Local dev (native processes — recommended for this environment)

```bash
make setup      # creates the Python venv, installs web deps, copies .env.example -> .env
make migrate    # applies Alembic migrations
make seed       # creates the admin user + DEMO DATA (idempotent-ish, --force to override)
make dev        # runs API on :8000 and Web on :3000
make health     # checks /api/v1/system/health
```

## On a Mac mini with more RAM

Edit `.env`:

```env
OLLAMA_MODEL=qwen2.5:7b        # or a larger model if RAM allows
LLM_MODEL=qwen2.5:7b
EMBEDDING_MODEL=nomic-embed-text
```

No code change is required — `meza/llm/factory.py` reads the model name
purely from settings.

## Docker Compose (hosts with a working Docker daemon)

```bash
cp .env.example .env   # edit as needed
docker compose up -d --build
docker compose exec api .venv/bin/meza create-admin
docker compose exec api .venv/bin/meza seed
```

## Autostart on the Mac mini (§61)

See `infrastructure/launchd/README.md` for both options (launchd vs. Docker
restart policy). Pick one — don't run both, they'd both bind port 8000.

## LAN access

Find the Mac mini's LAN IP (`ipconfig getifaddr en0` on Wi-Fi, or `en1`/
`en0` depending on interface) and set `CORS_ORIGINS` in `.env` to include
`http://<lan-ip>:3000`. Do not port-forward 8000/3000 to the public
internet (§60) — MEZA is an internal system.

## Rolling back a migration

```bash
cd apps/api && .venv/bin/alembic downgrade -1
```
