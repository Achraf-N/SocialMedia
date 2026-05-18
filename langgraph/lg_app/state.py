"""Chat state definition for LangGraph."""

from typing_extensions import TypedDict
from typing import Optional


class ChatState(TypedDict):
    """State definition for the conversational AI workflow."""
    session_id: str
    shop_id: str  # Shop ID to fetch products from backend
    message: str
    intent: Optional[str]
    product_query: Optional[str]
    active_product: Optional[str]
    active_product_id: Optional[str]
    active_product_name: Optional[str]
    current_product_id: Optional[str]
    current_product: Optional[str]
    current_product_name: Optional[str]
    delivery_city: Optional[str]
    delivery_address: Optional[str]
    pending_order_json: Optional[dict]
    shop_info: Optional[dict]
    catalog_filter: Optional[str]
    last_catalog_products: Optional[list[str]]
    response: Optional[str]
    steps: list[str]
    shop_data: list[dict]
    needs_human: bool
    confidence: float  # Router confidence score (0-1)
