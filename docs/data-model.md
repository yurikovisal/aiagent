# Data Model

55 tables across the domains in §40 of the master prompt, all defined in
`apps/api/meza/models/`, migrated with Alembic (`apps/api/alembic/`).

## Domains

- **auth**: `users`, `roles`
- **org**: `departments`, `employees`, `kpis`, `attendance`, `employee_reports`
- **crm**: `customers`, `deals`
- **projects**: `projects`, `tasks`
- **orders**: `orders`, `order_items`
- **production**: `work_centers`, `production_orders`, `production_stages`,
  `stage_dependencies`, `material_requirements`, `workflows`
- **warehouse**: `materials`, `warehouses`, `locations`, `inventory` (stock),
  `batches`, `inventory_movements`, `reservations`, `inventory_counts`
- **procurement**: `suppliers`, `purchase_requests`, `purchase_orders`,
  `supplier_offers`
- **finance**: `costs` (plan/actual, category), `payments`, `expenses`
- **documents**: `documents`, `document_chunks` (embeddings)
- **tenders**: `tenders`
- **marketing**: `campaigns`, `leads`, `content_items`
- **events/risk**: `events`, `risk_rules`, `risks`, `alerts`
- **ai governance**: `agents`, `agent_runs`, `tool_calls`, `llm_calls`,
  `approvals`, `audit_log`
- **memory**: `conversations`, `messages`, `business_memory`
- **imports**: `import_jobs`, `inbox_items`

## Conventions

- Every business table that can hold synthetic data carries `is_demo:
  bool` (`DemoMixin`) — never mixed with real data; `meza seed` refuses to
  run if non-demo orders already exist unless `--force` is passed.
- Timestamps are stored as naive UTC (`meza.core.utils.utcnow()`), so
  PostgreSQL and SQLite behave identically.
- Money fields are plain `Float` (management-accounting precision is
  adequate; this is explicitly not a ledger — see §17 and
  `docs/architecture.md`).
- `as_dict()` (via `Base.as_dict()`) is the canonical way to turn an ORM row
  into a JSON-safe dict for API responses and tool results.

## Production dependency modeling (§14)

`work_centers.sequence` gives a default linear order; `stage_dependencies`
lets a specific production order override that with an explicit DAG.
`work_centers.slot_based` + `slot_interval_days` model batch-scheduled
resources (e.g. a powder-coating oven that only runs every N days) — the
delay-propagation rule (`meza/rules/production.py::propagate_delay`) adds
the extra wait when an inherited delay causes a stage to miss its slot.

## Event model (§8)

`events` is an append-only log (`event_type`, `entity_type`, `entity_id`,
`source`, `timestamp`, `payload`, `severity`, `processed`,
`correlation_id`). The "What changed?" feature
(`meza/services/events.py::summarize_changes`) groups recent events by type
instead of asking the LLM to diff two large snapshots (§36).
