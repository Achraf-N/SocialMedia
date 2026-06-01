"""List products for selected shop."""

import json

from owner import owner_backend_client
from owner.nodes import error_message, is_error, list_from_response, require_shop
from owner.nodes.llm_response import generate_owner_response
from owner.owner_state import OwnerChatState


def list_products_node(state: OwnerChatState) -> OwnerChatState:
    if not require_shop(state):
        return state

    data = owner_backend_client.get_shop_products(state["selected_shop_id"])
    if is_error(data):
        state["response"] = error_message(data)
        state["steps"].append("List products failed")
        return state

    products = list_from_response(data, "products")
    if "out of stock" in state["message"].lower():
        products = [product for product in products if int(product.get("stock") or 0) == 0]
    state["last_products"] = products
    if products:
        first = products[0]
        state["last_product"] = {
            "id": first.get("id") or first.get("_id"),
            "name": first.get("name"),
            "price": first.get("price"),
            "stock": first.get("stock"),
        }
    if not products:
        state["response"] = "No matching products found for this shop."
    else:
        message = state["message"].lower()
        if "most expensive" in message or "highest price" in message:
            product = max(products, key=lambda item: float(item.get("price") or 0))
            fallback = "Most expensive product: " + _format_product(product)
            state["response"] = _generate_product_response(state, products, product) or fallback
            state["steps"].append("Listed most expensive product")
            return state
        if "cheapest" in message or "lowest price" in message:
            product = min(products, key=lambda item: float(item.get("price") or 0))
            fallback = "Cheapest product: " + _format_product(product)
            state["response"] = _generate_product_response(state, products, product) or fallback
            state["steps"].append("Listed cheapest product")
            return state

        parts = []
        for product in products:
            parts.append(_format_product(product))
        fallback = "Products: " + "; ".join(parts)
        state["response"] = _generate_product_response(state, products) or fallback
    state["steps"].append("Listed shop products")
    return state


def _format_product(product: dict) -> str:
    name = product.get("name") or "Unnamed product"
    price = product.get("price", "n/a")
    stock = product.get("stock", "n/a")
    available = product.get("available", stock != 0)
    return f"{name}: {price} MAD, stock {stock}, {'available' if available else 'unavailable'}"


def _generate_product_response(
    state: OwnerChatState,
    products: list[dict],
    selected_product: dict | None = None,
) -> str | None:
    compact_products = [
        {
            "name": product.get("name"),
            "price": product.get("price"),
            "stock": product.get("stock"),
            "available": product.get("available"),
            "category": product.get("category"),
            "brand": product.get("brand"),
        }
        for product in products
    ]
    compact_selected = None
    if selected_product:
        compact_selected = {
            "name": selected_product.get("name"),
            "price": selected_product.get("price"),
            "stock": selected_product.get("stock"),
            "available": selected_product.get("available"),
            "category": selected_product.get("category"),
            "brand": selected_product.get("brand"),
        }
    return generate_owner_response(
        "list_products",
        message=state["message"],
        shop_name=state.get("current_shop_name") or state.get("selected_shop_name") or "current shop",
        products=json.dumps(compact_products, ensure_ascii=False),
        selected_product=json.dumps(compact_selected, ensure_ascii=False),
    )
