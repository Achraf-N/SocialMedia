"""Owner help node."""

from owner.owner_state import OwnerChatState


def help_node(state: OwnerChatState) -> OwnerChatState:
    state["response"] = (
        "I can help you list shops, select a shop, view products, add products, "
        "update price, update stock, view orders, and update order status."
    )
    state["steps"].append("Generated owner help")
    return state
