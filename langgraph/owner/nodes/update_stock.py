"""Update product stock node."""

import re

from owner import owner_backend_client
from owner.nodes import backend_result_message, is_error, require_shop
from owner.owner_state import OwnerChatState


def _extract_stock_update(message: str) -> dict:
    data = {}
    name_patterns = [
        r"set\s+(.+?)\s+stock\s+to\s+\d+",
        r"increase\s+(.+?)\s+stock\s+by\s+\d+",
        r"decrease\s+(.+?)\s+stock\s+by\s+\d+",
        r"(.+?)\s+is\s+out\s+of\s+stock",
    ]
    for pattern in name_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            data["product_query"] = match.group(1).strip(" ,.")
            break
    set_match = re.search(r"\bstock\s+to\s+(\d+)\b", message, re.IGNORECASE)
    inc_match = re.search(r"\bincrease\b.+?\bby\s+(\d+)\b", message, re.IGNORECASE)
    dec_match = re.search(r"\bdecrease\b.+?\bby\s+(\d+)\b", message, re.IGNORECASE)
    if set_match:
        data["operation"] = "set"
        data["quantity"] = int(set_match.group(1))
    elif inc_match:
        data["operation"] = "increase"
        data["quantity"] = int(inc_match.group(1))
    elif dec_match:
        data["operation"] = "decrease"
        data["quantity"] = int(dec_match.group(1))
    elif "out of stock" in message.lower():
        data["operation"] = "set"
        data["quantity"] = 0
    return data


def update_stock_node(state: OwnerChatState) -> OwnerChatState:
    if not require_shop(state):
        return state

    data = _extract_stock_update(state["message"])
    missing = []
    if not data.get("product_query"):
        missing.append("product")
    if "operation" not in data or "quantity" not in data:
        missing.append("stock update")
    if missing:
        state["response"] = "Please specify " + ", ".join(missing) + "."
        state["needs_clarification"] = True
        state["steps"].append("Update stock unclear")
        return state

    result = owner_backend_client.update_product_stock(state["selected_shop_id"], data["product_query"], data)
    state["response"] = backend_result_message(result, "Stock updated.")
    state["steps"].append("Update stock failed" if is_error(result) else "Updated stock")
    return state
