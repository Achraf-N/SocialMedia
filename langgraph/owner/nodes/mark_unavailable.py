"""Mark product unavailable node."""

from owner import product_service
from owner.nodes import backend_result_message, is_error
from owner.nodes.product_helpers import product_id, product_name, resolve_single_product
from owner.owner_state import OwnerChatState


def mark_unavailable_node(state: OwnerChatState) -> OwnerChatState:
    product = resolve_single_product(state)
    if not product:
        return state

    result = product_service.mark_unavailable(state["selected_shop_id"], product_id(product))
    if is_error(result):
        state["response"] = backend_result_message(result, "Product could not be marked unavailable.")
        state["steps"].append("Mark unavailable failed")
        return state

    updated = result.get("product") if isinstance(result, dict) else {}
    updated = updated or {}
    state["last_product"] = {
        "id": updated.get("id") or product_id(product),
        "name": updated.get("name") or product_name(product),
        "price": updated.get("price", product.get("price")),
        "stock": updated.get("stock", product.get("stock")),
    }
    state["response"] = f"Done. {state['last_product']['name']} is now unavailable."
    state["steps"].append("Marked product unavailable")
    return state
