# MEZA Architecture

## Overview

```
USER
 -> MEZA UI (Next.js)
 -> MEZA Orchestrator (FastAPI, meza/orchestrator/core.py)
 -> Intent / Domain Router (meza/orchestrator/router.py)
 -> Specialized Agents (meza/agents/*, run in parallel per request)
 -> Tools (meza/tools/*) -> Database / Connectors / Files
 -> Result validation + Risk Engine + Approval Engine
 -> MEZA Synthesis (local LLM, deterministic fallback)
 -> USER
```

Specialized agents never talk to the user directly; only the orchestrator
does. This keeps the system auditable (`agent_runs`/`tool_calls`) and lets
new agents/tools be added without touching the UI.

## Layers

- **apps/api** — FastAPI application. `meza/core` (config, db, security,
  RBAC, logging, errors), `meza/models` (SQLAlchemy schema), `meza/rules`
  (pure, unit-tested business logic — margin, inventory shortage, production
  dependency propagation, risk scoring), `meza/services` (DB-backed read/
  write helpers used by tools and API routes), `meza/tools` (Tool Registry +
  concrete tools), `meza/agents` (Agent Protocol + 12 specialized agents),
  `meza/orchestrator` (router, executor with budget/RBAC enforcement, the
  MEZA orchestrator itself), `meza/connectors` (external-system adapter
  interfaces), `meza/api/v1` (versioned REST + WebSocket routes).
- **apps/web** — Next.js/TypeScript/Tailwind frontend.
- **packages/** — placeholder for code shared across apps if the system
  grows beyond the current monolithic API (kept minimal deliberately, see
  §78 priority: data > business logic > reliability > agent intelligence >
  UX > visual effects).

## Why a monolithic FastAPI app instead of microservices

A single internal user base, one Mac mini, and full local-first data all
argue against premature service splitting. `meza/agents`, `meza/tools`, and
`meza/connectors` are already separated cleanly enough that carving out a
service later (e.g. a dedicated Document Intelligence service) is a
refactor, not a rewrite.

## Request lifecycle (chat)

1. `POST /api/v1/meza/chat` or the `/api/v1/meza/ws` WebSocket receives the
   user's message.
2. `classify_intent` matches a few high-value phrasings (daily brief, what
   changed, why delayed, simulate) for future intent-specific handling;
   `route_domains` maps keywords to one or more of: sales, production,
   warehouse, procurement, finance, projects, documents, tenders,
   marketing, hr, overview.
3. Each routed domain's agent runs `asyncio.gather`'d in parallel
   (`meza/orchestrator/core.py::_run_domain`), each under its own timeout.
4. Every tool call an agent makes goes through `executor.execute_tool`,
   which checks RBAC permission, checks/decrements the per-run `Budget`
   (`max_steps`/`max_tool_calls`/`max_handoffs`, §30), executes the tool,
   and writes a `tool_calls` row + an `audit_log` row — whether it
   succeeded, failed, was denied, or is pending approval.
5. Results are merged: risks are deduplicated (`meza/rules/scoring.py`),
   findings/recommendations/sources are concatenated.
6. `synthesize()` asks the local LLM for a short executive-style answer
   grounded only in the merged agent summaries — if the LLM is unreachable,
   a deterministic concatenation of agent summaries is returned instead
   (§63: never a blank/broken response).
7. The `AgentRun` row is finalized with status/duration/token counts; the
   full `OrchestrationResult` (summary + risks + findings + recommendations
   + actions_proposed + sources + confidence) is returned to the UI.

## Data provenance & source of truth (§9/§66)

Every tool result that states a fact includes a `sources` entry (`{source,
record_id, timestamp, confidence}`) pointing at the DB table it came from.
Precedence when data conflicts: **Database > Connected system > Signed
document > User-confirmed data > AI inference.** MEZA never invents a
number; if a tool can't find something, it returns `ok=False` with an
explanation, which agents propagate as `status="insufficient_data"`.

## Approval Engine (§23)

Tools are tagged with a `ToolRisk`: `READ`, `CALCULATE`, `PROPOSE` execute
immediately; `WRITE_LOW_RISK`, `WRITE_HIGH_RISK`, `EXTERNAL_ACTION` create
an `Approval` row and stop — the actual write happens only from
`POST /api/v1/approvals/{id}/decide`, gated by `APPROVE_LOW`/`APPROVE_HIGH`
RBAC permissions (`meza/services/approvals.py`). See ADR 0004.

## Risk Engine (§38)

`meza/services/risk_engine.py` runs seven deterministic rules over
structured data (deadline-at-risk, material-below-min, receivable-overdue,
production-blocked, material-ETA-late, task-overdue, cost-overrun) and
upserts `Risk` rows keyed by a stable fingerprint so re-running the rules
doesn't create duplicates. The LLM is only used to explain/correlate
already-detected risks in the synthesized chat answer — never to invent
them.
