"""Application errors with human-readable explanations (no bare 'Something went wrong')."""

from __future__ import annotations


class MezaError(Exception):
    status_code = 400
    code = "meza_error"

    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(MezaError):
    status_code = 404
    code = "not_found"


class PermissionDeniedError(MezaError):
    status_code = 403
    code = "permission_denied"


class ApprovalRequiredError(MezaError):
    status_code = 409
    code = "approval_required"


class ValidationFailedError(MezaError):
    status_code = 422
    code = "validation_failed"


class ConnectorUnavailableError(MezaError):
    status_code = 503
    code = "connector_unavailable"


class BudgetExceededError(MezaError):
    status_code = 429
    code = "budget_exceeded"
