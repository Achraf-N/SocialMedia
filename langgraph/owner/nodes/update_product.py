"""Update product metadata node."""

import re

from owner import owner_backend_client
from owner.nodes import backend_result_message, is_error, require_shop
from owner.owner_state import OwnerChatState


def _extract_update_product(message: str) -> tuple[str | None, dict]:
    product_match = re.search(r"(?:update product|edit product|change product info)\s+(.+?)(?=\s+description\b|\s+category\b|\s+brand\b|$)", message, re.IGNORECASE)
    product_query = product_match.group(1).strip(" ,.") if product_match else None
    update_data = {}
    for field in ("description", "category", "brand"):
        match = re.search(rf"\b{field}\s+(.+?)(?=\s+description\b|\s+category\b|\s+brand\b|$)", message, re.IGNORECASE)
        if match:
            update_data[field] = match.group(1).strip(" ,.")
    return product_query, update_data


def update_product_node(state: OwnerChatState) -> OwnerChatState:
    if not require_shop(state):
        return state

    product_query, update_data = _extract_update_product(state["message"])
    missing = []
    if not product_query:
        missing.append("product")
    if not update_data:
        missing.append("fields to update")
    if missing:
        state["response"] = "Please specify " + ", ".join(missing) + "."
        state["needs_clarification"] = True
        state["steps"].append("Update product unclear")
        return state

    result = owner_backend_client.update_product(state["selected_shop_id"], product_query, update_data)
    state["response"] = backend_result_message(result, "Product updated.")
    state["steps"].append("Update product failed" if is_error(result) else "Updated product")
    return state
