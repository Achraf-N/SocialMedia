"""Node: Save session state."""

from lg_app.state import ChatState
from lg_app.memory.session_store import save_session_state


def save_session_state_node(state: ChatState) -> ChatState:
    """Save session state to memory."""
    save_session_state(
        state["session_id"],
        shop_id=state.get("shop_id"),
        active_product=state["active_product"],
        active_product_id=state.get("active_product_id"),
        active_product_name=state.get("active_product_name"),
        current_product_id=state.get("current_product_id"),
        current_product_name=state.get("current_product_name"),
        last_intent=state["intent"],
        extracted_city=state.get("delivery_city"),
        extracted_address=state.get("delivery_address"),
        pending_order_json=state.get("pending_order_json"),
        last_catalog_products=state.get("last_catalog_products"),
        clear_pending_order=state.get("pending_order_json") is None,
    )
    
    if state["active_product"]:
        state["steps"].append(f"Saved session: product={state['active_product']}, intent={state['intent']}")
    else:
        state["steps"].append(f"Saved session: intent={state['intent']}")
    
    return state
