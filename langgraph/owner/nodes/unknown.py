"""Owner unknown intent node."""

from owner.owner_state import OwnerChatState


def unknown_node(state: OwnerChatState) -> OwnerChatState:
    state["response"] = "Could you clarify what you want to manage?"
    state["needs_clarification"] = True
    state["steps"].append("Owner unknown response")
    return state
