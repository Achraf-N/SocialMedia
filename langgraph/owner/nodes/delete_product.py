"""Delete product node with mandatory confirmation."""

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


def delete_product_node(state: OwnerChatState) -> OwnerChatState:
    pending = pop_matching_confirmation(state, "delete_product")
    if pending:
        result = product_service.delete_product(pending["shop_id"], pending["product_id"])
        if is_error(result):
            state["response"] = backend_result_message(result, "Product could not be deleted.")
            state["steps"].append("Delete product failed")
            return state
        state["last_product"] = {}
        state["response"] = f"Done. Deleted {pending.get('product_name') or 'the product'}."
        state["steps"].append("Deleted product")
        return state

    payload = router_payload(state)
    product = resolve_single_product(state)
    if not product:
        return state

    set_pending_confirmation(
        state,
        "delete_product",
        product,
        payload,
        f"Please confirm: do you want to delete {product_name(product)} permanently?",
    )
    state["steps"].append(f"Delete product pending confirmation: {product_id(product)}")
    return state
