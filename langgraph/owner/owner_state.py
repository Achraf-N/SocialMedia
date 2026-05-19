"""State definition for the owner management agent."""

from typing import Optional
from typing_extensions import TypedDict


class OwnerChatState(TypedDict):
    owner_id: str
    message: str
    selected_shop_id: Optional[str]
    selected_shop_name: Optional[str]
    current_shop_id: Optional[str]
    current_shop_name: Optional[str]
    last_shops: list[dict]
    intent: Optional[str]
    response: Optional[str]
    steps: list[str]
    extracted_data: dict
    confidence: float
    needs_clarification: bool
