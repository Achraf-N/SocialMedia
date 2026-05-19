"""List products for selected shop."""

from owner import owner_backend_client
from owner.nodes import error_message, is_error, list_from_response, require_shop
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
    if not products:
        state["response"] = "No products found for this shop."
    else:
        parts = []
        for product in products:
            name = product.get("name") or "Unnamed product"
            price = product.get("price", "n/a")
            stock = product.get("stock", "n/a")
            available = product.get("available", stock != 0)
            parts.append(f"{name}: {price} MAD, stock {stock}, {'available' if available else 'unavailable'}")
        state["response"] = "Products: " + "; ".join(parts)
    state["steps"].append("Listed shop products")
    return state
