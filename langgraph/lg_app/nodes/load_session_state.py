"""Node: Load session state."""

from lg_app.state import ChatState
from lg_app.memory.session_store import get_session_state


def load_session_state(state: ChatState) -> ChatState:
    """Load previous session state."""
    session = get_session_state(state["session_id"])
    state["active_product"] = session.get("active_product")
    
    if state["active_product"]:
        state["steps"].append(f"Loaded active product from session: {state['active_product']}")
    else:
        state["steps"].append("Loaded session state (no active product)")
    
    return state
