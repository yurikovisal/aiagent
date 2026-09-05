# Connectors (§43)

`meza/connectors/base.py` defines the adapter interfaces real ATON+ systems
will eventually implement:

- `CRMConnector` — external CRM (Bitrix24, amoCRM, ...). Until implemented,
  `deals`/`customers` in MEZA's own database are the source of truth.
- `WarehouseConnector` — external WMS.
- `AccountingConnector` — external accounting/1C system. MEZA's Finance
  Controller is explicitly a *management accounting* layer, not a
  replacement (§17).
- `ProductionConnector` — external MES.

Two connectors are fully implemented today because they don't depend on any
external ATON+ system:

- `FileConnector` — reads local files (backs the Document Agent / Inbox).
- `SpreadsheetConnector` — reads CSV/XLSX/JSON rows (backs the Import
  Center, `meza/services/import_center.py`).

## Import Center (§44)

`POST /api/v1/imports/upload` (multipart, `target_entity` = `materials` or
`suppliers`) → column detection → suggested mapping
(`meza/services/import_center.py::suggest_mapping`) → the caller can adjust
mapping via `POST /api/v1/imports/{id}/mapping` → validation → preview
(first 10 rows) → `POST /api/v1/imports/{id}/confirm` actually writes rows.
Nothing is imported before that last explicit confirmation step.

## Inbox (§45)

`POST /api/v1/inbox/drop` accepts an arbitrary file, extracts text,
classifies it with the same rules as the Document Agent, and proposes an
action (`create_warehouse_receipt`, `create_document`, or
`review_manually`) without doing anything yet. A human calls
`POST /api/v1/inbox/{id}/accept` or `/reject`.

## Adding a real connector later

1. Implement the relevant `*Connector` ABC in `meza/connectors/`.
2. Add a `.env` entry for its base URL/credentials (never hard-code them).
3. Swap the direct DB read in the matching `meza/services/*.py` helper for
   a call through the connector, behind the same function signature, so
   tools and agents don't need to change.
