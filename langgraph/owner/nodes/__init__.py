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
    current_shop_id = state.get("current_shop_id") or state.get("selected_shop_id")
    current_shop_name = state.get("current_shop_name") or state.get("selected_shop_name")
    if current_shop_id:
        state["selected_shop_id"] = current_shop_id
        state["selected_shop_name"] = current_shop_name
        state["current_shop_id"] = current_shop_id
        state["current_shop_name"] = current_shop_name
        return True

    resolved_shop = resolve_shop_reference(state)
    if resolved_shop:
        state["selected_shop_id"] = str(resolved_shop.get("id") or resolved_shop.get("_id"))
        state["selected_shop_name"] = str(resolved_shop.get("name") or state["selected_shop_id"])
        state["current_shop_id"] = state["selected_shop_id"]
        state["current_shop_name"] = state["selected_shop_name"]
        state["steps"].append("Resolved current shop from previous shop list")
        return True

    shops_response = owner_backend_client.get_owner_shops(state["owner_id"])
    if is_error(shops_response):
        state["response"] = "Which shop would you like to manage?"
    else:
        shops = list_from_response(shops_response, "shops")
        if len(shops) > 1:
            names = [str(shop.get("name") or shop.get("id") or shop.get("_id")) for shop in shops]
            state["response"] = "Which shop would you like to manage? Available shops: " + ", ".join(names) + "."
        else:
            state["response"] = "Which shop would you like to manage?"
    state["needs_clarification"] = True
    state["steps"].append("Missing selected shop")
    return False


def resolve_shop_reference(state: OwnerChatState) -> dict | None:
    shops = state.get("last_shops") or []
    if not shops:
        return None

    message = state["message"].lower()
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

    if len(shops) == 1 and re.search(r"\b(this|that|the)\s+shops?\b", message):
        return shops[0]

    return None


def backend_result_message(data: Any, default: str) -> str:
    if is_error(data):
        return error_message(data)
    if isinstance(data, dict):
        return str(data.get("message") or data.get("detail") or default)
    return default
