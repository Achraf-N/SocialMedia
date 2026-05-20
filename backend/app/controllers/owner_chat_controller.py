"""Backend endpoint for the LangGraph owner chatbot."""

import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.database import owners_collection, shops_collection


CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
LANGGRAPH_DIR = PROJECT_ROOT / "langgraph"

if LANGGRAPH_DIR.exists() and str(LANGGRAPH_DIR) not in sys.path:
    sys.path.insert(0, str(LANGGRAPH_DIR))

try:
    from owner.owner_runner import run_owner_chat
except Exception:
    run_owner_chat = None


router = APIRouter(tags=["owner-chat"])


class OwnerChatRequest(BaseModel):
    message: str


class OwnerChatResponse(BaseModel):
    response: str
    intent: Optional[str] = None
    selected_shop_id: Optional[str] = None
    selected_shop_name: Optional[str] = None
    current_shop_id: Optional[str] = None
    current_shop_name: Optional[str] = None
    steps: list[str] = Field(default_factory=list)


@router.post("/owner/chat", response_model=OwnerChatResponse)
def owner_chat(
    request: OwnerChatRequest,
) -> OwnerChatResponse:
    if run_owner_chat is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Owner chat service failed",
        )

    try:
        from owner import owner_backend_client

        owner = _get_test_owner()
        owner_context = owner_backend_client.set_current_owner_id(str(owner["_id"]))
        try:
            result = run_owner_chat(owner_id=str(owner["_id"]), message=request.message)
        finally:
            owner_backend_client.reset_current_owner_id(owner_context)

        return OwnerChatResponse(
            response=result["response"],
            intent=result.get("intent"),
            selected_shop_id=result.get("selected_shop_id"),
            selected_shop_name=result.get("selected_shop_name"),
            current_shop_id=result.get("current_shop_id"),
            current_shop_name=result.get("current_shop_name"),
            steps=result.get("steps", []),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Owner chat service failed",
        )


def _get_test_owner() -> dict:
    """Temporary no-auth owner lookup for local testing."""
    for owner in owners_collection.find({}):
        if shops_collection.find_one({"owner_id": owner["_id"]}):
            return owner
    owner = owners_collection.find_one({})
    if owner:
        return owner
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No owner found for owner chat testing",
    )
