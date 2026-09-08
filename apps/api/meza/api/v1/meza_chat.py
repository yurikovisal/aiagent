"""MEZA chat, brief, and 'what changed' endpoints (§34/§35/§36/§42).

The response streams operational status over WebSocket while several agents run in parallel,
then delivers the final structured+synthesized answer. A plain POST endpoint is also provided
for programmatic / non-streaming callers. Both paths persist Conversation Memory (§26) the same
way — a follow-up in the same conversation gets recent prior turns as context.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from meza.api.deps import get_current_user
from meza.core.db import get_db, session_scope
from meza.core.security import decode_token
from meza.models import User
from meza.orchestrator.core import run_orchestration
from meza.services import conversations as conv_svc
from meza.services.brief import build_executive_brief
from meza.services.events import summarize_changes

router = APIRouter(prefix="/api/v1/meza", tags=["meza"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: int | None = None


@router.post("/chat")
async def chat(payload: ChatRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    conv = await conv_svc.get_or_create(db, user_id=user.id, conversation_id=payload.conversation_id, title_hint=payload.message)
    history = await conv_svc.recent_history(db, conv.id, limit=6)
    await conv_svc.append_message(db, conversation_id=conv.id, role="user", content=payload.message)
    result = await run_orchestration(db, request=payload.message, user_id=user.id, role=user.role, conversation_id=conv.id, history=history)
    await conv_svc.append_message(db, conversation_id=conv.id, role="assistant", content=result.summary, run_id=result.run_id, structured=result.as_dict())
    await db.commit()
    return {"conversation_id": conv.id, **result.as_dict()}


@router.websocket("/ws")
async def chat_ws(websocket: WebSocket):
    """Streams operational status ('Анализирую производство...') while agents run, then the
    final answer. Chain-of-thought is never exposed — only high-level operational status (§42)."""
    await websocket.accept()
    token = websocket.query_params.get("token")
    try:
        payload = decode_token(token) if token else None
    except Exception:
        payload = None
    if not payload:
        await websocket.send_json({"type": "error", "message": "Не авторизовано."})
        await websocket.close()
        return
    user_id = int(payload["sub"])
    role = payload["role"]
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            conversation_id = data.get("conversation_id")
            if not message:
                continue

            async def status_cb(evt: dict) -> None:
                await websocket.send_json(evt)

            async with session_scope() as db:
                conv = await conv_svc.get_or_create(db, user_id=user_id, conversation_id=conversation_id, title_hint=message)
                history = await conv_svc.recent_history(db, conv.id, limit=6)
                await conv_svc.append_message(db, conversation_id=conv.id, role="user", content=message)
                result = await run_orchestration(
                    db, request=message, user_id=user_id, role=role,
                    conversation_id=conv.id, history=history, status_cb=status_cb,
                )
                await conv_svc.append_message(db, conversation_id=conv.id, role="assistant", content=result.summary,
                                               run_id=result.run_id, structured=result.as_dict())
            await websocket.send_json({"type": "result", "conversation_id": conv.id, **result.as_dict()})
    except WebSocketDisconnect:
        return


@router.get("/brief")
async def brief(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await build_executive_brief(db)


@router.get("/changes")
async def changes(hours: int = 24, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await summarize_changes(db, hours=hours)


@router.get("/conversations")
async def list_conversations(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await conv_svc.list_for_user(db, user.id)
    return [r.as_dict() for r in rows]


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select

    from meza.models import Message

    rows = (await db.execute(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at))).scalars().all()
    return [r.as_dict() for r in rows]
