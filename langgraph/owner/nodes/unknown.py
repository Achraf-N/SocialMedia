"""Owner unknown intent node."""

from owner.nodes.llm_response import generate_owner_response
from owner.owner_state import OwnerChatState


def unknown_node(state: OwnerChatState) -> OwnerChatState:
    state["response"] = (
        generate_owner_response("unknown", message=state["message"])
        or "Could you clarify what you want to manage?"
    )
    state["needs_clarification"] = True
    state["steps"].append("Owner unknown response")
    return state
