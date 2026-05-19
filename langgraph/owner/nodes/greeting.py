"""Owner greeting node."""

from owner.owner_state import OwnerChatState


def greeting_node(state: OwnerChatState) -> OwnerChatState:
    state["response"] = "Hello. I can help you manage shops, products, stock, prices, and orders."
    state["steps"].append("Generated owner greeting")
    return state
