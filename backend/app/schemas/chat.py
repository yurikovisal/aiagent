from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import MessageRole


class ConversationCreate(BaseModel):
    title: str = Field(default="Новый чат", max_length=300)


class ConversationOut(BaseModel):
    id: UUID
    title: str
    model: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: UUID
    role: MessageRole
    content: str
    model: str | None = None
    latency_ms: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSendRequest(BaseModel):
    content: str = Field(min_length=1, max_length=16000)
    stream: bool = True
