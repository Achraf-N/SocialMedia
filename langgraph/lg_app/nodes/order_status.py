"""Node: Order status lookup agent."""

import requests

from lg_app import backend_client
from lg_app.state import ChatState


def _latest_order(orders: list[dict]) -> dict | None:
    if not orders:
        return None
    return orders[0]


def _product_summary(order: dict) -> str:
    items = order.get("items") or []
    if not items:
        return "your order"

    parts = []
    for item in items:
        name = item.get("product_name") or "product"
        quantity = item.get("quantity") or 1
        parts.append(f"{quantity} x {name}")
    return ", ".join(parts)


def _total_summary(order: dict) -> str:
    total = order.get("total_price")
    if total is None:
        return ""
    return f" Total: {total} MAD."


def order_status_agent(state: ChatState) -> ChatState:
    """Read the latest order status for this customer session."""
    try:
        data = backend_client.get_orders_by_session(state["shop_id"], state["session_id"])
        orders = data.get("orders", []) if isinstance(data, dict) else data
        order = _latest_order(orders)

        if not order:
            state["response"] = "I could not find any orders for this chat yet."
            state["steps"].append("No session orders found")
            return state

        status = order.get("status", "pending")
        order_id = order.get("id") or order.get("order_id")
        summary = _product_summary(order)
        total = _total_summary(order)
        if order_id:
            state["response"] = f"Your latest order ({summary}) is currently {status}.{total} Order ID: {order_id}."
        else:
            state["response"] = f"Your latest order ({summary}) is currently {status}.{total}"
        state["steps"].append("Read latest order status")
    except requests.HTTPError as exc:
        detail = "I could not check your order status right now."
        response = exc.response
        if response is not None:
            try:
                detail_value = response.json().get("detail")
                if detail_value:
                    detail = str(detail_value)
            except ValueError:
                pass
        state["response"] = detail
        state["steps"].append("Order status lookup failed")
    except Exception:
        state["response"] = "I could not reach the order service right now."
        state["steps"].append("Order status service unavailable")

    return state
