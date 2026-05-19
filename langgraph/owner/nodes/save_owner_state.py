"""Persist owner state after each turn."""

from owner.owner_memory import save_owner_state
from owner.owner_state import OwnerChatState


def save_owner_state_node(state: OwnerChatState) -> OwnerChatState:
    save_owner_state(
        state["owner_id"],
        state.get("selected_shop_id"),
        state.get("selected_shop_name"),
        state.get("intent"),
    )
    state["steps"].append("Saved owner context")
    return state
