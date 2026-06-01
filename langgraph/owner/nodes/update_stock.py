"""Update product stock node."""

from owner import product_service
from owner.nodes import backend_result_message, is_error
from owner.nodes.product_helpers import (
    pop_matching_confirmation,
    product_id,
    product_name,
    resolve_single_product,
    router_payload,
    set_pending_confirmation,
)
from owner.owner_state import OwnerChatState


def update_stock_node(state: OwnerChatState) -> OwnerChatState:
    pending = pop_matching_confirmation(state, "update_stock")
    if pending:
        payload = pending.get("payload") or {}
        operation = payload.get("stock_operation") or {}
        result = product_service.update_stock(
            pending["shop_id"],
            pending["product_id"],
            operation.get("type"),
            operation.get("quantity"),
        )
        return _finish_stock_update(state, result, pending.get("product_name"))

    payload = router_payload(state)
    if state.get("confidence", 0.0) < 0.70:
        state["response"] = "Please clarify the stock change."
        state["needs_clarification"] = True
        return state

    operation = payload.get("stock_operation") or {}
    op_type = operation.get("type")
    quantity = operation.get("quantity")
    if op_type not in {"set", "increment", "decrement"} or quantity is None:
        state["response"] = "Please specify the stock operation and quantity."
        state["needs_clarification"] = True
        return state

    product = resolve_single_product(state)
    if not product:
        return state

    if op_type == "set" and int(quantity) == 0 and "out of stock" not in state["message"].lower() and "unavailable" not in state["message"].lower():
        set_pending_confirmation(
            state,
            "update_stock",
            product,
            payload,
            f"Please confirm: set {product_name(product)} stock to 0?",
        )
        state["steps"].append("Stock zero requires confirmation")
        return state

    result = product_service.update_stock(state["selected_shop_id"], product_id(product), op_type, int(quantity))
    return _finish_stock_update(state, result, product_name(product))


def _finish_stock_update(state: OwnerChatState, result: dict, name: str | None) -> OwnerChatState:
    if is_error(result):
        state["response"] = backend_result_message(result, "Stock could not be updated.")
        state["steps"].append("Update stock failed")
        return state
    product = result.get("product") if isinstance(result, dict) else {}
    product = product or {}
    display_name = name or product.get("name") or "the product"
    stock = product.get("stock")
    state["last_product"] = {
        "id": product.get("id"),
        "name": product.get("name") or display_name,
        "price": product.get("price"),
        "stock": stock,
    }
    state["response"] = f"Done. {display_name} stock is now {stock}."
    state["steps"].append("Updated stock")
    return state
