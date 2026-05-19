"""Deterministic owner-agent intent router."""

import re

from owner.owner_state import OwnerChatState


VALID_STATUSES = {"pending", "confirmed", "processing", "shipped", "delivered", "cancelled"}


def _contains(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _extract_status(text: str) -> str | None:
    for status in VALID_STATUSES:
        if status in text:
            return status
    if "cancel order" in text or text.startswith("cancel "):
        return "cancelled"
    return None


def _extract_order_id(message: str) -> str | None:
    match = re.search(r"\border\s+([A-Za-z0-9_-]+)\b", message, re.IGNORECASE)
    return match.group(1) if match else None


def owner_router(state: OwnerChatState) -> OwnerChatState:
    """Route owner message to an intent and capture lightweight fields."""
    text = state["message"].strip()
    lower = text.lower()
    extracted = {}
    intent = "unknown"

    if _contains(lower, ["hello", "hi", "salam", "hey"]):
        intent = "greeting"
    elif _contains(lower, ["help", "what can you do", "how can you help me"]):
        intent = "help"
    elif _contains(lower, ["show my shops", "list my shops", "what shops do i have", "my stores", "my shops"]):
        intent = "list_shops"
    elif _contains(lower, ["select ", "use shop ", "choose shop ", "switch to ", "work on this shop", "choose shop id"]):
        intent = "select_shop"
        extracted["shop_query"] = re.sub(
            r"^(select|use shop|choose shop|switch to|work on|choose shop id)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
    elif _contains(lower, ["shop summary", "shop overview", "how is my shop doing", "what is happening in my store", "business overview"]):
        intent = "shop_summary"
    elif _contains(lower, ["show products", "list products", "what products are in this shop", "show stock", "inventory", "stock list"]):
        intent = "list_products"
    elif _contains(lower, ["add product", "create new product", "new product"]):
        intent = "add_product"
    elif _contains(lower, ["set price", "change ", "update price"]) and "price" in lower:
        intent = "update_price"
    elif _contains(lower, ["set ", "increase ", "decrease ", "out of stock", "update stock"]) and "stock" in lower:
        intent = "update_stock"
    elif _contains(lower, ["update product", "change product description", "edit product", "change product info"]):
        intent = "update_product"
    elif _contains(lower, ["mark order", "set order", "cancel order", "update order status"]):
        intent = "update_order_status"
        extracted["order_id"] = _extract_order_id(text)
        extracted["status"] = _extract_status(lower)
    elif _contains(lower, ["show pending orders", "show orders", "what orders do i have", "orders today", "pending orders"]):
        intent = "list_orders"
        status = _extract_status(lower)
        if status:
            extracted["status"] = status

    state["intent"] = intent
    state["extracted_data"] = {**state.get("extracted_data", {}), **extracted}
    state["confidence"] = 0.95 if intent != "unknown" else 0.4
    state["steps"].append(f"Owner router intent: {intent}")
    return state
