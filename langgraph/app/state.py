"""Chat state definition for LangGraph."""

from typing_extensions import TypedDict
from typing import Optional


class ChatState(TypedDict):
    """State definition for the conversational AI workflow."""
    session_id: str
    message: str
    intent: Optional[str]
    product_query: Optional[str]
    active_product: Optional[str]
    response: Optional[str]
    steps: list[str]
    shop_data: list[dict]
    needs_human: bool
    confidence: float  # Router confidence score (0-1)
