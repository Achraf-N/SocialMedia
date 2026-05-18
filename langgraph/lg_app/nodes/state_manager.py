"""Node: Update active product."""

from lg_app.state import ChatState


def _find_active_product(state: ChatState) -> dict | None:
    for product in state.get("shop_data", []):
        if product.get("name") == state.get("active_product"):
            return product
    return None


def _product_id(product: dict) -> str | None:
    product_id = product.get("id") or product.get("_id")
    return str(product_id) if product_id is not None else None


def update_active_product(state: ChatState) -> ChatState:
    """
    Update active product from product query or keep previous.
    
    Rules:
    - If product_query exists, set active_product = product_query
    - Else keep previous active_product
    """
    previous_product_id = state.get("active_product_id") or state.get("current_product_id")
    previous_product_name = state.get("active_product_name") or state.get("active_product")

    if state["product_query"]:
        state["active_product"] = state["product_query"]
        state["active_product_name"] = state["product_query"]
        state["steps"].append(f"Set active product to: {state['active_product']}")
    elif state["active_product"]:
        state["active_product_name"] = state.get("active_product_name") or state["active_product"]
        state["steps"].append(f"Kept active product: {state['active_product']}")
    else:
        state["active_product_name"] = None
        state["steps"].append("No active product")

    state["current_product"] = state["active_product"]
    state["current_product_name"] = state["active_product"]
    product = _find_active_product(state)
    if product:
        state["active_product_id"] = _product_id(product)
        state["active_product_name"] = product.get("name")
        state["current_product_id"] = state["active_product_id"]
        state["current_product_name"] = state["active_product_name"]
    elif state.get("current_product_id") and not state.get("active_product_id"):
        state["active_product_id"] = state["current_product_id"]
    product_changed = (
        previous_product_id
        and state.get("active_product_id")
        and previous_product_id != state.get("active_product_id")
    ) or (
        previous_product_name
        and state.get("active_product_name")
        and previous_product_name != state.get("active_product_name")
    )
    if product_changed:
        state["pending_order_json"] = None
        state["steps"].append("Cleared pending order after product change")

    return state
