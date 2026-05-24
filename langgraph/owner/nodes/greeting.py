"""Owner greeting node."""

from owner.nodes.llm_response import generate_owner_response
from owner.owner_state import OwnerChatState


def greeting_node(state: OwnerChatState) -> OwnerChatState:
    response = generate_owner_response("greeting", message=state["message"])
    state["response"] = response or "Hello. I can help you manage shops, products, stock, prices, and orders."
    state["steps"].append("Generated owner greeting")
    return state
