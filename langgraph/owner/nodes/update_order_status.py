"""Update order status node."""

import re

from owner import owner_backend_client
from owner.nodes import backend_result_message, is_error
from owner.owner_state import OwnerChatState


ALLOWED_STATUSES = {"pending", "confirmed", "processing", "shipped", "delivered", "cancelled"}


def _extract_order_update(message: str) -> dict:
    lower = message.lower()
    data = {}
    order_match = re.search(r"\border\s+([A-Za-z0-9_-]+)\b", message, re.IGNORECASE)
    if order_match:
        data["order_id"] = order_match.group(1)
    for status in ALLOWED_STATUSES:
        if status in lower:
            data["status"] = status
            break
    if "cancel order" in lower and "status" not in data:
        data["status"] = "cancelled"
    return data


def update_order_status_node(state: OwnerChatState) -> OwnerChatState:
    data = {**_extract_order_update(state["message"]), **state.get("extracted_data", {})}
    missing = []
    if not data.get("order_id"):
        missing.append("order_id")
    if data.get("status") not in ALLOWED_STATUSES:
        missing.append("status")
    if missing:
        state["response"] = "Please send " + ", ".join(missing) + "."
        state["needs_clarification"] = True
        state["steps"].append("Update order status missing fields")
        return state

    result = owner_backend_client.update_order_status(data["order_id"], data["status"])
    state["response"] = backend_result_message(result, "Order status updated.")
    state["steps"].append("Update order status failed" if is_error(result) else "Updated order status")
    return state
