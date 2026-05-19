"""Add product node."""

import re

from owner import owner_backend_client
from owner.nodes import backend_result_message, is_error, require_shop
from owner.owner_state import OwnerChatState


REQUIRED_FIELDS = ("name", "price", "category", "stock")


def _extract_add_product(message: str) -> dict:
    data = {}
    name_match = re.search(r"(?:add product|new product|create new product)\s+(.+?)(?=\s+price\b|\s+stock\b|\s+category\b|$)", message, re.IGNORECASE)
    if name_match:
        data["name"] = name_match.group(1).strip(" ,.")
    price_match = re.search(r"\bprice\s+(\d+(?:\.\d+)?)\b", message, re.IGNORECASE)
    if price_match:
        data["price"] = float(price_match.group(1))
    stock_match = re.search(r"\bstock\s+(\d+)\b", message, re.IGNORECASE)
    if stock_match:
        data["stock"] = int(stock_match.group(1))
    category_match = re.search(r"\bcategory\s+(.+?)(?=\s+price\b|\s+stock\b|\s+description\b|\s+brand\b|$)", message, re.IGNORECASE)
    if category_match:
        data["category"] = category_match.group(1).strip(" ,.")
    for field in ("description", "brand", "image", "delivery_time"):
        match = re.search(rf"\b{field.replace('_', ' ')}\s+(.+?)(?=\s+price\b|\s+stock\b|\s+category\b|\s+description\b|\s+brand\b|\s+image\b|\s+delivery time\b|$)", message, re.IGNORECASE)
        if match:
            data[field] = match.group(1).strip(" ,.")
    return data


def add_product_node(state: OwnerChatState) -> OwnerChatState:
    if not require_shop(state):
        return state

    product_data = _extract_add_product(state["message"])
    missing = [field for field in REQUIRED_FIELDS if product_data.get(field) in (None, "")]
    if missing:
        state["response"] = "Please send " + ", ".join(missing) + "."
        state["needs_clarification"] = True
        state["extracted_data"] = {**state.get("extracted_data", {}), "product_data": product_data}
        state["steps"].append(f"Add product missing fields: {', '.join(missing)}")
        return state

    result = owner_backend_client.create_product(state["selected_shop_id"], product_data)
    state["response"] = backend_result_message(result, "Product created.")
    if is_error(result):
        state["steps"].append("Create product failed")
    else:
        state["steps"].append("Created product")
    return state
