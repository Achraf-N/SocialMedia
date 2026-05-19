"""Shop summary node."""

from owner import owner_backend_client
from owner.nodes import error_message, is_error, list_from_response, require_shop
from owner.owner_state import OwnerChatState


def shop_summary_node(state: OwnerChatState) -> OwnerChatState:
    if not require_shop(state):
        return state

    products_data = owner_backend_client.get_shop_products(state["selected_shop_id"])
    if is_error(products_data):
        state["response"] = error_message(products_data)
        state["steps"].append("Shop summary products failed")
        return state

    orders_data = owner_backend_client.get_shop_orders(state["selected_shop_id"])
    if is_error(orders_data):
        state["response"] = error_message(orders_data)
        state["steps"].append("Shop summary orders failed")
        return state

    products = list_from_response(products_data, "products")
    orders = list_from_response(orders_data, "orders")
    low_stock = [p for p in products if int(p.get("stock") or 0) <= 3]
    pending_orders = [o for o in orders if o.get("status") == "pending"]
    shop_name = state.get("selected_shop_name") or "this shop"
    state["response"] = (
        f"{shop_name} summary: {len(products)} products, "
        f"{len(low_stock)} low-stock products, {len(pending_orders)} pending orders."
    )
    state["steps"].append("Generated shop summary")
    return state
