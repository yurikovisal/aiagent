# Security

- **Authentication**: email + bcrypt password hash, JWT access tokens
  (`meza/core/security.py`), delivered either as `Authorization: Bearer` or
  an httpOnly session cookie.
- **RBAC**: six roles (`ADMIN, DIRECTOR, DEPARTMENT_HEAD, MANAGER,
  EMPLOYEE, VIEWER`) mapped to a fixed permission set
  (`meza/core/rbac.py`). Permissions are checked **server-side** on every
  API route (`Depends(require_permission(...))`) and on every tool call
  (`meza/orchestrator/executor.py`) — never only hidden in the UI.
- **Approval Engine**: see `docs/architecture.md` and ADR 0004. No agent
  can mutate business data without a human decision for anything above
  `PROPOSE` risk.
- **Audit log**: every tool call (success, failure, denial, or pending
  approval) and every approval decision is written to `audit_log`
  (`meza/services/audit.py`), with who/when/what/result.
- **Validation**: Pydantic models validate every request body; file uploads
  are checked against an extension allowlist and a size limit
  (`MAX_UPLOAD_MB`).
- **Rate limiting**: a per-IP fixed-window limiter
  (`meza/api/middleware.py::RateLimitMiddleware`), `RATE_LIMIT_PER_MINUTE`
  in `.env`. Swap for a Redis-backed limiter if MEZA is ever scaled beyond
  a single node.
- **Secrets**: only ever read from environment variables
  (`meza/core/config.py`); `.env` is git-ignored, `.env.example` ships with
  placeholders only. `meza/core/logging.py` scrubs anything that looks like
  a password/token/secret before it reaches a log line.
- **CORS**: locked to `CORS_ORIGINS` (defaults to the local web app only).
- **Security headers**: `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Permissions-Policy` set on every response.
- **Network**: MEZA is designed to run entirely on the local network. Do
  not expose port 8000/3000 directly to the public internet (§60); use a
  VPN or the office LAN if remote access is needed.

## Threat model notes specific to an agentic system

- Tool inputs are validated Pydantic/JSON-schema shapes, not raw LLM
  free-text passed straight to SQL — every tool builds parameterized
  SQLAlchemy queries.
- The LLM is never given write capability directly; it can only cause a
  `WRITE_*`/`EXTERNAL_ACTION` tool call to be *proposed*, which then must
  clear the Approval Engine.
- Execution budgets (`meza/orchestrator/executor.py::Budget`) bound the
  blast radius of any single request regardless of what the LLM decides to
  do.
