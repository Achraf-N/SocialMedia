"""List orders node."""

from owner import owner_backend_client
from owner.nodes import error_message, is_error, list_from_response, require_shop
from owner.owner_state import OwnerChatState


def list_orders_node(state: OwnerChatState) -> OwnerChatState:
    if not require_shop(state):
        return state

    status = state.get("extracted_data", {}).get("status")
    data = owner_backend_client.get_shop_orders(state["selected_shop_id"], status=status)
    if is_error(data):
        state["response"] = error_message(data)
        state["steps"].append("List orders failed")
        return state

    orders = list_from_response(data, "orders")
    if not orders:
        state["response"] = f"No {status or ''} orders found.".replace("  ", " ").strip()
    else:
        parts = []
        for order in orders[:10]:
            order_id = order.get("id") or order.get("_id") or order.get("order_id")
            order_status = order.get("status", "pending")
            total = order.get("total_price", "n/a")
            parts.append(f"{order_id}: {order_status}, total {total}")
        state["response"] = "Orders: " + "; ".join(parts)
    state["steps"].append("Listed shop orders")
    return state
