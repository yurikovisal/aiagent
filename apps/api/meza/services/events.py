"""Event log (§8/§36). Every important change becomes an event; 'what changed' reads this log
instead of asking the LLM to diff two large snapshots."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.core.utils import new_id, utcnow
from meza.models import Event

SEVERITIES = ("INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL")


async def emit(
    db: AsyncSession,
    *,
    event_type: str,
    entity_type: str,
    entity_id: str | int,
    payload: dict | None = None,
    source: str = "system",
    severity: str = "INFO",
    correlation_id: str | None = None,
) -> Event:
    ev = Event(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=str(entity_id),
        source=source,
        timestamp=utcnow(),
        payload=payload or {},
        severity=severity,
        processed=False,
        correlation_id=correlation_id or new_id(),
    )
    db.add(ev)
    await db.flush()
    return ev


async def recent_events(db: AsyncSession, *, hours: int = 24, event_type: str | None = None, limit: int = 100) -> list[dict]:
    cutoff = utcnow() - timedelta(hours=hours)
    q = select(Event).where(Event.timestamp >= cutoff)
    if event_type:
        q = q.where(Event.event_type == event_type)
    q = q.order_by(Event.timestamp.desc()).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [r.as_dict() for r in rows]


async def summarize_changes(db: AsyncSession, hours: int = 24) -> dict:
    """Group recent events by type for the 'What changed?' view — deterministic, no LLM."""
    rows = await recent_events(db, hours=hours, limit=1000)
    by_type: dict[str, list[dict]] = {}
    for r in rows:
        by_type.setdefault(r["event_type"], []).append(r)
    return {
        "hours": hours,
        "total": len(rows),
        "by_type": {k: {"count": len(v), "items": v[:20]} for k, v in sorted(by_type.items(), key=lambda kv: -len(kv[1]))},
    }
