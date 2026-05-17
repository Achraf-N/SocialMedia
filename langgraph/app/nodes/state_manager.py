"""Node: Update active product."""

from app.state import ChatState


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
    
    return state
