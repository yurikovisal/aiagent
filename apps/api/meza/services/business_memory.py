"""Business Memory (§26): confirmed ATON+ knowledge, distinct from Conversation Memory (dialogue
context) and Operational State (the live DB). Never a source of truth for money/stock/orders —
only for durable facts a human has explicitly confirmed (a policy, a client preference, a
standing instruction) that agents should keep in mind when reasoning."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.core.utils import utcnow
from meza.models import BusinessMemory


async def create_confirmed(db: AsyncSession, *, key: str, content: str, category: str, user_id: int) -> BusinessMemory:
    """A human directly asserting a fact (e.g. via Settings) — confirmed immediately, no
    approval workflow needed since a person is typing/confirming it themselves."""
    entry = BusinessMemory(key=key, content=content, category=category, confirmed_by_user_id=user_id,
                            confirmed=True, created_at=utcnow())
    db.add(entry)
    await db.flush()
    return entry


async def propose(db: AsyncSession, *, key: str, content: str, category: str) -> BusinessMemory:
    """An agent proposing a fact be remembered — unconfirmed until a human approves it via the
    Approval Engine (meza/services/approvals.py handles the actual confirm-on-approve)."""
    entry = BusinessMemory(key=key, content=content, category=category, confirmed_by_user_id=None,
                            confirmed=False, created_at=utcnow())
    db.add(entry)
    await db.flush()
    return entry


async def confirm(db: AsyncSession, memory_id: int, *, user_id: int) -> BusinessMemory | None:
    entry = await db.get(BusinessMemory, memory_id)
    if not entry:
        return None
    entry.confirmed = True
    entry.confirmed_by_user_id = user_id
    await db.flush()
    return entry


async def search(db: AsyncSession, query: str, *, category: str | None = None, confirmed_only: bool = True, limit: int = 10) -> list[BusinessMemory]:
    q = select(BusinessMemory)
    if confirmed_only:
        q = q.where(BusinessMemory.confirmed.is_(True))
    if category:
        q = q.where(BusinessMemory.category == category)
    if query:
        q = q.where(BusinessMemory.key.ilike(f"%{query}%") | BusinessMemory.content.ilike(f"%{query}%"))
    q = q.order_by(BusinessMemory.created_at.desc()).limit(limit)
    return list((await db.execute(q)).scalars().all())


async def list_all(db: AsyncSession, *, confirmed_only: bool = False) -> list[BusinessMemory]:
    q = select(BusinessMemory).order_by(BusinessMemory.created_at.desc())
    if confirmed_only:
        q = q.where(BusinessMemory.confirmed.is_(True))
    return list((await db.execute(q)).scalars().all())


async def delete(db: AsyncSession, memory_id: int) -> bool:
    entry = await db.get(BusinessMemory, memory_id)
    if not entry:
        return False
    await db.delete(entry)
    await db.flush()
    return True
