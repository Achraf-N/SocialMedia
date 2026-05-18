"""Node: Load session state."""

from lg_app.state import ChatState
from lg_app.memory.session_store import get_session_state


def load_session_state(state: ChatState) -> ChatState:
    """Load previous session state."""
    session = get_session_state(state["session_id"], state.get("shop_id"))
    state["active_product"] = session.get("active_product")
    state["active_product_id"] = session.get("active_product_id") or session.get("current_product_id")
    state["active_product_name"] = session.get("active_product_name") or session.get("current_product_name") or state["active_product"]
    state["current_product_id"] = state["active_product_id"]
    state["current_product"] = state["active_product"]
    state["current_product_name"] = state["active_product_name"]
    state["delivery_city"] = session.get("extracted_city")
    state["delivery_address"] = session.get("extracted_address")
    state["pending_order_json"] = session.get("pending_order_json")
    state["last_catalog_products"] = session.get("last_catalog_products")
    
    if state["active_product"]:
        state["steps"].append(f"Loaded active product from session: {state['active_product']}")
    else:
        state["steps"].append("Loaded session state (no active product)")
    
    return state
