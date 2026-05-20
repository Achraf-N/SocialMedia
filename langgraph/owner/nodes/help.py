"""Owner help node."""

from owner.nodes.llm_response import generate_owner_response
from owner.owner_state import OwnerChatState


def help_node(state: OwnerChatState) -> OwnerChatState:
    fallback = (
        "I can help you list shops, select a shop, view products, add products, "
        "update price, update stock, view orders, and update order status."
    )
    state["response"] = generate_owner_response("help", message=state["message"]) or fallback
    state["steps"].append("Generated owner help")
    return state
