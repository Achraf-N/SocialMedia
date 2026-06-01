"""Get product detail node."""

import re

from owner.nodes.product_helpers import format_money, product_name, resolve_single_product
from owner.owner_state import OwnerChatState


def get_product_node(state: OwnerChatState) -> OwnerChatState:
    product = resolve_single_product(state)
    if not product:
        return state

    state["last_product"] = {
        "id": product.get("id"),
        "name": product_name(product),
        "price": product.get("price"),
        "stock": product.get("stock"),
    }
    if _is_price_question(state["message"]):
        state["response"] = f"The price of {product_name(product)} is {format_money(product.get('price'))}."
        state["steps"].append("Returned product price")
        return state

    availability = "available" if product.get("available", product.get("stock", 0) != 0) else "unavailable"
    state["response"] = (
        f"{product_name(product)}: {format_money(product.get('price'))}, "
        f"stock {product.get('stock', 'n/a')}, {availability}."
    )
    state["steps"].append("Returned product detail")
    return state


def _is_price_question(message: str) -> bool:
    lower = message.lower()
    return bool(re.search(r"\b(?:price|cost|how\s+much)\b", lower))
