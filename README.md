# MEZA — ATON+ Internal AI Operating System

MEZA is ATON+'s local-first, internal AI operating system: it collects
company data, coordinates specialized AI agents, runs a deterministic Risk
Engine, and gives leadership grounded answers with visible evidence and
controlled actions.

This is **not** a SaaS product, has no pricing/billing, and is not intended
for external customers — see `docs/architecture.md` for the full picture.

## Quick start

```bash
make setup      # venv + web deps + .env
make migrate    # apply DB schema
make seed       # create admin user + DEMO DATA (clearly flagged, never real data)
make dev        # API on :8000, Web on :3000
```

Then open http://localhost:3000, log in with the admin credentials printed
by `make seed` (from `.env`: `ADMIN_EMAIL` / `ADMIN_PASSWORD`), and ask
MEZA: *"Что сейчас требует моего внимания?"*

## Documentation

- `docs/current-state.md` — Phase 0 environment audit (hardware, runtimes,
  what was actually found vs. assumed)
- `docs/architecture.md` — system design, request lifecycle, approval/risk engines
- `docs/agents.md` — agent protocol, registered agents, router
- `docs/data-model.md` — the 55-table schema
- `docs/security.md`, `docs/deployment.md`, `docs/backup-restore.md`,
  `docs/connectors.md`
- `docs/decisions/` — architecture decision records

## Project layout

```
apps/api      FastAPI backend (agents, tools, orchestrator, business rules, API)
apps/web      Next.js frontend
packages/     shared code placeholders for future extraction
infrastructure/  launchd plists (Mac mini autostart) 
scripts/      backup/restore
storage/      uploads, inbox, backups (git-ignored except .gitkeep)
```

## Local LLM

Runs entirely on [Ollama](https://ollama.com) — no data leaves the
machine. Default model is configurable via `.env` (`OLLAMA_MODEL`), not
hard-coded anywhere in the codebase.
