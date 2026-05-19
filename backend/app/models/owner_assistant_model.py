from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    shop_id: str | None = None


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class MessageAppend(BaseModel):
    role: Literal["owner", "assistant"]
    content: str = Field(min_length=1)


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: datetime


class ConversationResponse(BaseModel):
    id: str
    owner_id: str
    shop_id: str | None
    title: str | None
    created_at: datetime
    updated_at: datetime


class ConversationWithMessagesResponse(BaseModel):
    id: str
    owner_id: str
    shop_id: str | None
    title: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse]
