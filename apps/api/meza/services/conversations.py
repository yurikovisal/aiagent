"""Conversation Memory (§26): dialogue context only — never a source of truth for business facts
(orders/stock/money always come from tools against the live DB, per meza/orchestrator/reasoning.py).
This service just persists turns and hands back recent ones so a follow-up question can refer to
what was just discussed.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.core.utils import utcnow
from meza.models import Conversation, Message


async def get_or_create(db: AsyncSession, *, user_id: int, conversation_id: int | None, title_hint: str) -> Conversation:
    if conversation_id:
        conv = await db.get(Conversation, conversation_id)
        if conv and conv.user_id == user_id:
            return conv
    conv = Conversation(user_id=user_id, title=title_hint[:80], created_at=utcnow(), updated_at=utcnow())
    db.add(conv)
    await db.flush()
    return conv


async def append_message(db: AsyncSession, *, conversation_id: int, role: str, content: str,
                          run_id: str | None = None, structured: dict | None = None) -> Message:
    msg = Message(conversation_id=conversation_id, role=role, content=content, run_id=run_id,
                  structured=structured, created_at=utcnow())
    db.add(msg)
    conv = await db.get(Conversation, conversation_id)
    if conv:
        conv.updated_at = utcnow()
    await db.flush()
    return msg


async def recent_history(db: AsyncSession, conversation_id: int, *, limit: int = 6) -> list[dict]:
    """Last `limit` turns, oldest first, as plain role/content dicts for the synthesis prompt."""
    q = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    rows = list((await db.execute(q)).scalars().all())
    rows.reverse()
    return [{"role": m.role, "content": m.content} for m in rows]


async def list_for_user(db: AsyncSession, user_id: int, *, limit: int = 30) -> list[Conversation]:
    q = select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc()).limit(limit)
    return list((await db.execute(q)).scalars().all())
