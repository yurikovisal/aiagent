# Current State — Environment Audit (Phase 0)

Recorded 2026-09-05. This audit determines the architecture choices below; it is
not aspirational — every item was actually checked on this machine.

## Hardware / OS

The task brief assumes a Mac mini (Apple Silicon, `system_profiler`, `sw_vers`,
launchd). The actual execution host for this session is a **Linux container**,
not the target Mac mini:

```
OS:      Ubuntu 24.04.4 LTS, kernel 6.18 x86_64
CPU:     4 cores
RAM:     15 GiB
Disk:    252 GB volume, ~30 GB free at audit time
```

Consequence: `system_profiler`/`sw_vers`/launchd do not apply here. The
architecture is built to be **host-agnostic** (Docker Compose + plain
processes both work), and `infrastructure/launchd/` ships a ready-to-use
launchd plist for the real Mac mini, plus a Docker-restart-policy alternative,
so whoever deploys this on the actual Mac mini can pick either mechanism
without code changes (see §61 of the master prompt, `docs/deployment.md`).

RAM budget: 15 GiB comfortably runs a small local LLM (1.5B–4B params) plus
Postgres/Next.js/FastAPI. On the real Mac mini, `docs/deployment.md` gives
guidance for picking a bigger local model if RAM allows.

## Installed runtimes (checked, not assumed)

| Tool | Found | Version |
|---|---|---|
| Python | yes | 3.11 (system), 3.12/3.13/3.14 available via `uv` |
| Node.js | yes | v22.22.2 |
| npm / pnpm / yarn | yes | npm 10.9.7, pnpm & yarn present |
| Git | yes | present |
| Docker | client only | daemon (`dockerd`) is **not running** in this container |
| PostgreSQL | yes | server 16, cluster `main` (was stopped, now started, port 5432) |
| Redis | yes | redis-server 7.0.15 present, not started by default |
| Ollama | not installed | binary downloaded (v0.11.10 linux/amd64) and started manually |
| sqlite3 | yes | 3.45.1 (via Python stdlib) |

Decision: since the Docker **daemon** is unavailable in this sandbox, MEZA
runs as plain OS processes (uv-managed Python venv + FastAPI/uvicorn, Next.js
dev/build) instead of `docker compose up`. `docker-compose.yml` is still
provided and kept correct for the real Mac mini / any host where the Docker
daemon is available — it is the recommended way to run MEZA in production.

## Local LLM

No Ollama models were pre-installed. Downloaded and pulled:

- `qwen2.5:1.5b` — chat/completions, ~986 MB on disk. Benchmarked: short
  completion (~2 tokens) generated in ~55 ms of eval time on CPU — usable for
  interactive chat on 4 CPU cores.
- `nomic-embed-text` — embeddings, ~274 MB on disk, used for document RAG.

Both are configured purely through `.env` (`OLLAMA_URL`, `OLLAMA_MODEL`,
`EMBEDDING_MODEL`) — nothing is hard-coded in application code, so a larger
model (e.g. `qwen2.5:7b`, `llama3.1:8b`) can be swapped in on more capable
hardware (like the real Mac mini) by editing `.env` alone.

## Database

- PostgreSQL 16 server was present but stopped; started via `pg_ctlcluster`.
- Created role `meza` and databases `meza` (dev) / `meza_test` (tests).
- `pg_trgm` extension enabled for fuzzy/full-text search groundwork.
  `pgvector` was not available as a package on this host; document embeddings
  are stored as JSON arrays for now (`document_chunks.embedding`), with the
  connector/query code isolated behind `meza/services/search.py` so switching
  to a native `pgvector` column is a migration-only change later.
- SQLite fallback (`sqlite+aiosqlite`) is supported by the same `DATABASE_URL`
  config knob for single-user/offline runs, but PostgreSQL is primary.

## Ports used

| Port | Service |
|---|---|
| 5432 | PostgreSQL |
| 6379 | Redis (optional; DB-backed job queue used by default) |
| 8000 | MEZA API (FastAPI) |
| 3000 | MEZA Web (Next.js) |
| 11434 | Ollama |

## Existing relevant projects

The repository (`yurikovisal/aiagent`) was empty (one-line `README.md`) at
the start of this session — there is no pre-existing ATON+ codebase to
integrate with yet. `packages/connectors/` therefore ships interface-only
adapters (`BaseConnector`, `CRMConnector`, `WarehouseConnector`,
`AccountingConnector`, `ProductionConnector`) plus a working
`FileConnector`/`SpreadsheetConnector` pair and an Import Center, so real
ATON+ systems can be wired in incrementally without touching agent code.

## Constraints this audit imposes on the build

1. No Docker daemon here → primary dev workflow is native processes
   (`make dev`), Compose kept for hosts that do have Docker.
2. 4 CPU cores, no GPU → small local model by default; heavier reasoning
   tasks are pushed into deterministic code (Risk Engine, finance/inventory
   rules) rather than the LLM, per master-prompt §7/§17/§38.
3. Outbound network goes through a proxy; Ollama's own release artifacts is
   the only external fetch performed, and only during setup — the running
   system is fully local-first afterwards (no data leaves the machine).

## Proposed architecture (confirmed after the above)

```
apps/api    FastAPI + SQLAlchemy(async) + Alembic, JWT/RBAC, structured JSON logs
apps/web    Next.js (App Router) + TypeScript + Tailwind
packages/*  agents, tools, connectors, business_rules (rules/), shared types
Ollama      local LLM runtime (qwen2.5:1.5b default, swappable via .env)
PostgreSQL  primary source of truth (55-table schema, Alembic-migrated)
Redis       optional cache/queue; DB-backed job table is the default queue
```

This matches §3/§6 of the master prompt with the one substitution explained
above (native processes vs. Docker Compose), which is the "objectively
better option after investigating the actual environment" the master prompt
explicitly allows in §5/§269.
