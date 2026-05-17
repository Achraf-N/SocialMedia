"""Node: Update active product."""

from lg_app.state import ChatState


def _find_active_product(state: ChatState) -> dict | None:
    for product in state.get("shop_data", []):
        if product.get("name") == state.get("active_product"):
            return product
    return None


def update_active_product(state: ChatState) -> ChatState:
    """
    Update active product from product query or keep previous.
    
    Rules:
    - If product_query exists, set active_product = product_query
    - Else keep previous active_product
    """
    if state["product_query"]:
        state["active_product"] = state["product_query"]
        state["steps"].append(f"Set active product to: {state['active_product']}")
    elif state["active_product"]:
        state["steps"].append(f"Kept active product: {state['active_product']}")
    else:
        state["steps"].append("No active product")

    state["current_product"] = state["active_product"]
    state["current_product_name"] = state["active_product"]
    product = _find_active_product(state)
    if product:
        state["current_product_id"] = product.get("id") or product.get("_id")
    
    return state
