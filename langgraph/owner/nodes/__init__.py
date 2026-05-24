"""Shared helpers for owner agent nodes."""

import re
from typing import Any

from owner import owner_backend_client
from owner.owner_state import OwnerChatState


def is_error(data: Any) -> bool:
    return isinstance(data, dict) and data.get("ok") is False


def error_message(data: Any) -> str:
    if isinstance(data, dict):
        return data.get("error") or "Backend request failed."
    return "Backend request failed."


def list_from_response(data: Any, key: str) -> list:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def require_shop(state: OwnerChatState) -> bool:
    if has_explicit_shop_reference(state["message"]):
        resolved_shop = resolve_shop_reference(state)
        if not resolved_shop:
            shops_response = owner_backend_client.get_owner_shops(state["owner_id"])
            if not is_error(shops_response):
                state["last_shops"] = list_from_response(shops_response, "shops")
                resolved_shop = resolve_shop_reference(state)

        if resolved_shop:
            set_current_shop(state, resolved_shop)
            state["steps"].append("Resolved explicit shop reference")
            return True

        shops = state.get("last_shops") or []
        names = [
            f"{index}. {shop.get('name') or shop.get('id') or shop.get('_id')}"
            for index, shop in enumerate(shops, start=1)
        ]
        state["response"] = "I could not find that shop."
        if names:
            state["response"] += " Available shops: " + ", ".join(names) + "."
        state["needs_clarification"] = True
        state["steps"].append("Explicit shop reference unclear")
        return False

    current_shop_id = state.get("current_shop_id") or state.get("selected_shop_id")
    current_shop_name = state.get("current_shop_name") or state.get("selected_shop_name")
    if current_shop_id:
        set_current_shop(state, {"id": current_shop_id, "name": current_shop_name})
        return True

    resolved_shop = resolve_shop_reference(state)
    if resolved_shop:
        set_current_shop(state, resolved_shop)
        state["steps"].append("Resolved current shop from previous shop list")
        return True

    last_shops = state.get("last_shops") or []
    if len(last_shops) == 1:
        set_current_shop(state, last_shops[0])
        state["steps"].append("Auto-selected only shop from previous shop list")
        return True

    shops_response = owner_backend_client.get_owner_shops(state["owner_id"])
    if is_error(shops_response):
        state["response"] = "Which shop would you like to manage?"
    else:
        shops = list_from_response(shops_response, "shops")
        state["last_shops"] = shops
        if len(shops) == 1:
            set_current_shop(state, shops[0])
            state["steps"].append("Auto-selected only owner shop")
            return True
        if len(shops) > 1:
            names = [str(shop.get("name") or shop.get("id") or shop.get("_id")) for shop in shops]
            state["response"] = "Which shop would you like to manage? Available shops: " + ", ".join(names) + "."
        else:
            state["response"] = "Which shop would you like to manage?"
    state["needs_clarification"] = True
    state["steps"].append("Missing selected shop")
    return False


def set_current_shop(state: OwnerChatState, shop: dict) -> None:
    shop_id = str(shop.get("id") or shop.get("_id"))
    shop_name = str(shop.get("name") or shop_id)
    state["selected_shop_id"] = shop_id
    state["selected_shop_name"] = shop_name
    state["current_shop_id"] = shop_id
    state["current_shop_name"] = shop_name


def has_explicit_shop_reference(message: str) -> bool:
    lowered = message.lower()
    return bool(
        re.search(r"\bshop\s*\d+\b", lowered)
        or re.search(r"\b\d+(?:st|nd|rd|th)?\s+shop\b", lowered)
        or re.search(r"\b(?:first|second|third|last|latest|final)\s+shops?\b", lowered)
    )


def resolve_shop_reference(state: OwnerChatState) -> dict | None:
    shops = state.get("last_shops") or []
    if not shops:
        return None

    message = state["message"].lower()
    numbered = re.search(r"\bshop\s*(\d+)\b", message) or re.search(
        r"\b(\d+)(?:st|nd|rd|th)?\s+shop\b",
        message,
    )
    if numbered:
        index = int(numbered.group(1)) - 1
        if 0 <= index < len(shops):
            return shops[index]
        return None

    ordinal_map = {
        "first": 0,
        "1st": 0,
        "one": 0,
        "second": 1,
        "2nd": 1,
        "two": 1,
        "third": 2,
        "3rd": 2,
        "three": 2,
    }
    for word, index in ordinal_map.items():
        if re.search(rf"\b(?:the\s+)?{word}\s+shop\b", message) and 0 <= index < len(shops):
            return shops[index]

    if re.search(r"\b(?:the\s+)?(?:last|latest|final)\s+shops?\b", message):
        return shops[-1]

    if len(shops) == 1 and re.search(r"\b(this|that|the|last)\s+shops?\b", message):
        return shops[0]

    return None


def backend_result_message(data: Any, default: str) -> str:
    if is_error(data):
        return error_message(data)
    if isinstance(data, dict):
        return str(data.get("message") or data.get("detail") or default)
    return default
