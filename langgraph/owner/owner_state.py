"""State definition for the owner management agent."""

from typing import Any, Optional
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
    router_output: dict
    pending_confirmation: dict
    pending_product_create: dict
    pending_action: Optional[dict[str, Any]]
    pending_field: Optional[dict[str, Any]]
    response_prefix: Optional[str]
    last_product: dict
    last_products: list[dict]
    confidence: float
    needs_clarification: bool
