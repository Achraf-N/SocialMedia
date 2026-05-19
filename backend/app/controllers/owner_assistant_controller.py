from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import owner_conversation_messages_collection, owner_conversations_collection
from app.core.dependencies import get_current_owner
from app.models.common import now_utc
from app.models.owner_assistant_model import (
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    ConversationWithMessagesResponse,
    MessageAppend,
    MessageResponse,
)

router = APIRouter(prefix="/assistant/conversations", tags=["owner-assistant"])


def _get_owned_conversation(conversation_id: str, owner: dict[str, Any]) -> dict:
    if not ObjectId.is_valid(conversation_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversation id")
    conv = owner_conversations_collection.find_one(
        {"_id": ObjectId(conversation_id), "owner_id": owner["_id"]}
    )
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conv


def _serialize_conversation(doc: dict) -> ConversationResponse:
    return ConversationResponse(
        id=str(doc["_id"]),
        owner_id=str(doc["owner_id"]),
        shop_id=str(doc["shop_id"]) if doc.get("shop_id") else None,
        title=doc.get("title"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


def _serialize_message(doc: dict) -> MessageResponse:
    return MessageResponse(
        id=str(doc["_id"]),
        conversation_id=str(doc["conversation_id"]),
        role=doc["role"],
        content=doc["content"],
        created_at=doc["created_at"],
    )


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    body: ConversationCreate,
    owner: dict = Depends(get_current_owner),
) -> ConversationResponse:
    now = now_utc()
    doc = {
        "owner_id": owner["_id"],
        "shop_id": ObjectId(body.shop_id) if body.shop_id and ObjectId.is_valid(body.shop_id) else None,
        "title": body.title,
        "created_at": now,
        "updated_at": now,
    }
    result = owner_conversations_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _serialize_conversation(doc)


@router.get("", response_model=list[ConversationResponse])
def list_conversations(owner: dict = Depends(get_current_owner)) -> list[ConversationResponse]:
    docs = owner_conversations_collection.find(
        {"owner_id": owner["_id"]},
        sort=[("updated_at", -1)],
    )
    return [_serialize_conversation(d) for d in docs]


@router.get("/{conversation_id}", response_model=ConversationWithMessagesResponse)
def get_conversation(
    conversation_id: str,
    owner: dict = Depends(get_current_owner),
) -> ConversationWithMessagesResponse:
    conv = _get_owned_conversation(conversation_id, owner)
    messages = list(
        owner_conversation_messages_collection.find(
            {"conversation_id": conv["_id"]},
            sort=[("created_at", 1)],
        )
    )
    return ConversationWithMessagesResponse(
        id=str(conv["_id"]),
        owner_id=str(conv["owner_id"]),
        shop_id=str(conv["shop_id"]) if conv.get("shop_id") else None,
        title=conv.get("title"),
        created_at=conv["created_at"],
        updated_at=conv["updated_at"],
        messages=[_serialize_message(m) for m in messages],
    )


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: str,
    body: ConversationUpdate,
    owner: dict = Depends(get_current_owner),
) -> ConversationResponse:
    conv = _get_owned_conversation(conversation_id, owner)
    updates: dict = {"updated_at": now_utc()}
    if body.title is not None:
        updates["title"] = body.title
    owner_conversations_collection.update_one({"_id": conv["_id"]}, {"$set": updates})
    conv.update(updates)
    return _serialize_conversation(conv)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    owner: dict = Depends(get_current_owner),
) -> None:
    conv = _get_owned_conversation(conversation_id, owner)
    owner_conversation_messages_collection.delete_many({"conversation_id": conv["_id"]})
    owner_conversations_collection.delete_one({"_id": conv["_id"]})


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def append_message(
    conversation_id: str,
    body: MessageAppend,
    owner: dict = Depends(get_current_owner),
) -> MessageResponse:
    conv = _get_owned_conversation(conversation_id, owner)
    now = now_utc()
    doc = {
        "conversation_id": conv["_id"],
        "role": body.role,
        "content": body.content,
        "created_at": now,
    }
    result = owner_conversation_messages_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    owner_conversations_collection.update_one({"_id": conv["_id"]}, {"$set": {"updated_at": now}})
    return _serialize_message(doc)


@router.delete("/{conversation_id}/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    conversation_id: str,
    message_id: str,
    owner: dict = Depends(get_current_owner),
) -> None:
    conv = _get_owned_conversation(conversation_id, owner)
    if not ObjectId.is_valid(message_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid message id")
    result = owner_conversation_messages_collection.delete_one(
        {"_id": ObjectId(message_id), "conversation_id": conv["_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
