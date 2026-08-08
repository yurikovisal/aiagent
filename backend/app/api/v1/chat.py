import json
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models import User
from app.schemas.chat import ChatSendRequest, ConversationCreate, ConversationOut, MessageOut
from app.services import chat as chat_service

router = APIRouter()


@router.get("/status")
async def chat_status():
    return {"ready": True, "phase": 1, "streaming": True}


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await chat_service.list_conversations(db, user)


@router.post("/conversations", response_model=ConversationOut, status_code=201)
async def create_conversation(
    body: ConversationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await chat_service.create_conversation(db, user, title=body.title)


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
async def get_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await chat_service.get_conversation(db, user, conversation_id)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = await chat_service.get_conversation(db, user, conversation_id)
    return conv.messages


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: UUID,
    body: ChatSendRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not body.stream:
        chunks: list[str] = []
        async for token in chat_service.stream_reply(db, user, conversation_id, body.content):
            chunks.append(token)
        return {"role": "assistant", "content": "".join(chunks)}

    async def event_stream():
        async for token in chat_service.stream_reply(db, user, conversation_id, body.content):
            payload = json.dumps({"token": token}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
        yield "data: {\"done\": true}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
