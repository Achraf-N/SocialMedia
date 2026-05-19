"""Shared helpers for owner agent nodes."""

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
    if state.get("selected_shop_id"):
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


def backend_result_message(data: Any, default: str) -> str:
    if is_error(data):
        return error_message(data)
    if isinstance(data, dict):
        return str(data.get("message") or data.get("detail") or default)
    return default
