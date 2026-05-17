"""Node: Save session state."""

from app.state import ChatState
from app.memory.session_store import save_session_state


def save_session_state_node(state: ChatState) -> ChatState:
    """Save session state to memory."""
    save_session_state(
        state["session_id"],
        active_product=state["active_product"],
        last_intent=state["intent"]
    )
    
    if state["active_product"]:
        state["steps"].append(f"Saved session: product={state['active_product']}, intent={state['intent']}")
    else:
        state["steps"].append(f"Saved session: intent={state['intent']}")
    
    return state
