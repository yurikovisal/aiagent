from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal


def utcnow() -> datetime:
    """Naive UTC timestamp (stored identically in PostgreSQL and SQLite)."""
    return datetime.now(UTC).replace(tzinfo=None)


def today() -> date:
    return utcnow().date()


def days_from_now(days: float) -> datetime:
    return utcnow() + timedelta(days=days)


def new_id() -> str:
    return uuid.uuid4().hex


def to_float(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, Decimal):
        return float(v)
    return float(v)


def jsonable(value):
    """Best-effort conversion of ORM / datetime / Decimal values into JSON-safe data."""
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set):
        return [jsonable(v) for v in value]
    if hasattr(value, "model_dump"):
        return jsonable(value.model_dump())
    if hasattr(value, "__table__"):
        return {c.name: jsonable(getattr(value, c.name)) for c in value.__table__.columns}
    return str(value)
