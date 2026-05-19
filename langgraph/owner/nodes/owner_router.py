"""Owner-agent intent router with deterministic and optional LLM modes."""

import json
import re

from owner.owner_state import OwnerChatState
from owner.prompts.router_prompt import OWNER_ROUTER_SYSTEM_PROMPT, OWNER_ROUTER_USER_PROMPT_TEMPLATE


VALID_STATUSES = {"pending", "confirmed", "processing", "shipped", "delivered", "cancelled"}
VALID_INTENTS = {
    "greeting",
    "list_shops",
    "select_shop",
    "shop_summary",
    "list_products",
    "add_product",
    "update_product",
    "update_stock",
    "update_price",
    "list_orders",
    "update_order_status",
    "help",
    "unknown",
}


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


def _parse_router_json(response_text: str) -> dict | None:
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _normalize_llm_result(result: dict) -> dict | None:
    intent = result.get("intent")
    if intent not in VALID_INTENTS:
        return None

    confidence = result.get("confidence", 0.85)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.85

    extracted_data = result.get("extracted_data") or {}
    if not isinstance(extracted_data, dict):
        extracted_data = {}

    return {
        "intent": intent,
        "confidence": max(0.0, min(confidence, 1.0)),
        "extracted_data": {
            key: value
            for key, value in extracted_data.items()
            if value not in (None, "", "null", "None")
        },
    }


def build_owner_router_prompt(state: OwnerChatState) -> tuple[str, str]:
    """Build system and user prompts for owner-agent LLM routing."""
    user_prompt = OWNER_ROUTER_USER_PROMPT_TEMPLATE.format(
        message=state["message"],
        selected_shop_id=state.get("selected_shop_id") or "None",
        selected_shop_name=state.get("selected_shop_name") or "None",
        last_intent=state.get("intent") or state.get("extracted_data", {}).get("last_intent") or "None",
    )
    return OWNER_ROUTER_SYSTEM_PROMPT, user_prompt


def route_with_llm(state: OwnerChatState, use_llm: bool = False) -> dict | None:
    """Classify owner intent with Ollama when explicitly enabled."""
    if not use_llm:
        return None

    try:
        from owner.llm import get_llm

        system_prompt, user_prompt = build_owner_router_prompt(state)
        response_text = get_llm().generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.0,
            max_tokens=256,
        )
        parsed = _parse_router_json(response_text)
        if not parsed:
            return None
        return _normalize_llm_result(parsed)
    except Exception:
        return None


def deterministic_owner_router(state: OwnerChatState) -> dict:
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

    return {
        "intent": intent,
        "extracted_data": extracted,
        "confidence": 0.95 if intent != "unknown" else 0.4,
    }


def owner_router(state: OwnerChatState) -> OwnerChatState:
    """Route owner message to an intent and capture lightweight fields."""
    router_result = route_with_llm(state, use_llm=True)
    if router_result is None:
        router_result = deterministic_owner_router(state)
        state["steps"].append("Owner router used deterministic fallback")
    else:
        state["steps"].append("Owner router used local LLM")

    state["intent"] = router_result["intent"]
    state["extracted_data"] = {
        **state.get("extracted_data", {}),
        **router_result.get("extracted_data", {}),
    }
    state["confidence"] = router_result["confidence"]
    state["steps"].append(f"Owner router intent: {state['intent']}")
    return state
