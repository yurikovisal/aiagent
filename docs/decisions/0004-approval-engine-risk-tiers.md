# 4. Tool risk tiers and the Approval Engine

Date: 2026-09-05

## Status
Accepted

## Context
§23 requires READ/CALCULATE/PROPOSE to run automatically, and WRITE_LOW_RISK/
WRITE_HIGH_RISK/EXTERNAL_ACTION to require a human decision proportional to
risk.

## Decision
`meza/tools/base.py` defines `ToolRisk` = READ, CALCULATE, PROPOSE,
WRITE_LOW_RISK, WRITE_HIGH_RISK, EXTERNAL_ACTION. The tool executor
(`meza/orchestrator/executor.py`) auto-runs the first three and, for the
other two, creates an `Approval` row and returns `PENDING_APPROVAL` instead
of executing — the write only happens from `POST /approvals/{id}/decide`
after a human with `APPROVE_LOW`/`APPROVE_HIGH` permission approves it.

## Consequences
No agent or tool can silently mutate business data; every WRITE_* / EXTERNAL
tool call is auditable end-to-end (`tool_calls` → `approvals` → `audit_log`).
