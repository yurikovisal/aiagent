# Agents

## Protocol (`meza/agents/base.py`)

Every agent implements `handle(ctx, request, params) -> AgentResult`, where
`AgentResult` is the common contract from §10:

```
status, summary, facts, findings, risks, recommendations,
actions_proposed, sources, confidence, data, error
```

No agent returns free-form text as its primary output — `summary` is a
short string for display, but every claim behind it is in `facts`/`sources`.

## Registered agents (`meza/agents/registry.py`)

| Agent | Domain(s) | Notes |
|---|---|---|
| MEZA Executive | overview/brief | Combines Risk Engine + event log for Daily Brief / Needs Attention |
| Sales Agent | sales | Deals, stalled-deal detection; CRM-adapter-ready, not CRM-locked |
| Production Planner | production | Stage status, downstream delay propagation |
| Warehouse Agent | warehouse | Stock, shortage, slow-moving materials |
| Procurement Agent | procurement | Availability check + **proposes** purchase requests (never buys) |
| Finance Controller | finance | Plan vs Actual margin, cost variance explanation |
| Project Manager | projects | Overdue tasks, blockers |
| Document Agent | documents | Search/classify documents |
| Tender Agent | tenders | Internal tender tracking + deadline risk; never auto-submits |
| Marketing Agent | marketing | Campaign/lead analytics only; no auto-publish |
| HR/KPI Agent | hr | Department workload from transparent, already-collected data only |
| Analytics Agent | overview (fan-out) | Runs the Risk Engine, aggregates cross-domain risk |

## Agent Router (`meza/orchestrator/router.py`)

Deterministic keyword matching maps free text to one or more domains before
any LLM call — cheap, explainable, and fast on a small local model. A vague
question ("что происходит?") fans out to the six core operational domains
plus the Risk-Engine-backed Analytics agent, so nothing gets silently
dropped just because the phrasing didn't hit a specific keyword.

## Execution budget (§30)

`meza/orchestrator/executor.py::Budget` bounds `max_steps`,
`max_tool_calls`, and `max_handoffs` per orchestration run (defaults from
`.env`: `MAX_AGENT_STEPS`, `MAX_AGENT_TOOL_CALLS`, `MAX_AGENT_HANDOFFS`).
Each agent additionally has a per-call `timeout_seconds` enforced with
`asyncio.wait_for` so one slow tool can't hang the whole chat response.

## Adding a new agent

1. Subclass `Agent` in `meza/agents/<name>.py`, set `agent_id`,
   `allowed_tools`, `risk_level`.
2. Register it in `meza/agents/registry.py` and add it to
   `DOMAIN_TO_AGENT` if it should be reachable from free-text routing.
3. Add any new tools it needs to `meza/tools/defs.py` with an explicit
   `ToolRisk` and `required_permission`.
4. Add a routing test (`tests/test_router.py`) and an agent-contract test
   (`tests/test_agent_contract.py`).

## Genuine reasoning vs. deterministic fast paths (§28)

Every agent's `handle()` follows the same shape:

1. If the router already extracted an exact identifier (an order number, a material SKU) —
   handle it deterministically, no LLM call. Cheap and 100% reliable.
2. Otherwise, if the free-text request plausibly needs interpretation (a per-agent keyword
   heuristic — see each agent's `_looks_targeted`/`_looks_specific` helper), call
   `self.reason(ctx, request, budget)`, which runs the shared ReAct loop
   (`meza/orchestrator/reasoning.py`, see ADR 0005) letting the LLM pick tools and extract
   parameters from the sentence.
3. If neither applies (or reasoning returns nothing usable), fall back to the agent's own broad
   deterministic scan (e.g. Warehouse's low-stock list, Procurement's low-stock summary).

The reasoning loop's output is never trusted for facts — only for phrasing and which tools to
call. All numbers, sources, and risks in the final `AgentResult` come from the `ToolResult`
objects the loop actually collected.

## Business Memory as agent context (§26)

`get_business_memory` (READ) is available to Sales, Procurement, and Document agents so a
confirmed standing fact (a client's payment terms, a supplier arrangement) can inform an
answer. `remember_business_fact` (WRITE_LOW_RISK) lets an agent *propose* adding a new fact,
gated by the Approval Engine exactly like a purchase request — it only becomes "confirmed" and
usable once a human approves it (`meza/services/approvals.py::_execute_approval`). A human can
also add a confirmed fact directly via Settings → Business Memory or `POST /api/v1/memory`,
which skips the approval step since a person is asserting it themselves.

## Configurable Risk Engine thresholds (§38)

`meza/services/risk_engine.py` no longer hard-codes its thresholds. Each rule's parameters
(e.g. `deadline_at_risk`'s `deadline_hours`/`progress_threshold`, `cost_overrun`'s
`threshold_pct`) live in the `risk_rules` table, editable via `GET/PATCH
/api/v1/risks/rules/{rule_key}` (also in Settings → Risk Engine in the UI) without a code
change or redeploy. `ensure_default_rules()` seeds sane defaults on first run; a rule can be
disabled entirely (`enabled=false`) without removing it.
