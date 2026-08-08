from __future__ import annotations

import time
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models import Conversation, Message, MessageRole, User
from app.services.llm.ollama_client import stream_chat
from app.services.llm.tracing import trace_generation


async def create_conversation(db: AsyncSession, user: User, title: str = "Новый чат") -> Conversation:
    settings = get_settings()
    conv = Conversation(user_id=user.id, title=title, model=settings.llm_model)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def list_conversations(db: AsyncSession, user: User) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_conversation(db: AsyncSession, user: User, conversation_id: UUID) -> Conversation:
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id, Conversation.user_id == user.id)
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conv


async def stream_reply(
    db: AsyncSession,
    user: User,
    conversation_id: UUID,
    content: str,
) -> AsyncIterator[str]:
    settings = get_settings()
    conv = await get_conversation(db, user, conversation_id)

    user_msg = Message(conversation_id=conv.id, role=MessageRole.user, content=content)
    db.add(user_msg)
    await db.commit()

    history = [
        {"role": "system", "content": settings.system_prompt},
        *[
            {"role": m.role.value, "content": m.content}
            for m in conv.messages
            if m.role in (MessageRole.user, MessageRole.assistant, MessageRole.system)
        ],
        {"role": "user", "content": content},
    ]

    started = time.perf_counter()
    chunks: list[str] = []
    with trace_generation(
        name="chat.stream",
        model=settings.llm_model,
        user_id=str(user.id),
        input_text=content,
    ) as trace_ctx:
        async for token in stream_chat(history, model=conv.model or settings.llm_model):
            chunks.append(token)
            yield token
        full = "".join(chunks)
        trace_ctx["output"] = full

    latency_ms = int((time.perf_counter() - started) * 1000)
    assistant = Message(
        conversation_id=conv.id,
        role=MessageRole.assistant,
        content="".join(chunks),
        model=conv.model or settings.llm_model,
        latency_ms=latency_ms,
    )
    db.add(assistant)
    if conv.title == "Новый чат" and content.strip():
        conv.title = content.strip()[:80]
    await db.commit()
