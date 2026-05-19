"""Update product price node."""

import re

from owner import owner_backend_client
from owner.nodes import backend_result_message, is_error, require_shop
from owner.owner_state import OwnerChatState


def _extract_price_update(message: str) -> dict:
    patterns = [
        r"change\s+(.+?)\s+price\s+to\s+(\d+(?:\.\d+)?)",
        r"set\s+price\s+of\s+(.+?)\s+to\s+(\d+(?:\.\d+)?)",
        r"update\s+price\s+of\s+(.+?)\s+to\s+(\d+(?:\.\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return {"product_query": match.group(1).strip(" ,."), "price": float(match.group(2))}
    return {}


def update_price_node(state: OwnerChatState) -> OwnerChatState:
    if not require_shop(state):
        return state

    data = _extract_price_update(state["message"])
    missing = []
    if not data.get("product_query"):
        missing.append("product")
    if "price" not in data:
        missing.append("price")
    if missing:
        state["response"] = "Please specify " + ", ".join(missing) + "."
        state["needs_clarification"] = True
        state["steps"].append("Update price unclear")
        return state

    result = owner_backend_client.update_product_price(state["selected_shop_id"], data["product_query"], data["price"])
    state["response"] = backend_result_message(result, "Price updated.")
    state["steps"].append("Update price failed" if is_error(result) else "Updated price")
    return state
