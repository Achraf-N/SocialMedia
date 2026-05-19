"""Persist owner state after each turn."""

from owner.owner_memory import save_owner_state
from owner.owner_state import OwnerChatState


def save_owner_state_node(state: OwnerChatState) -> OwnerChatState:
    current_shop_id = state.get("current_shop_id") or state.get("selected_shop_id")
    current_shop_name = state.get("current_shop_name") or state.get("selected_shop_name")
    state["selected_shop_id"] = current_shop_id
    state["selected_shop_name"] = current_shop_name
    state["current_shop_id"] = current_shop_id
    state["current_shop_name"] = current_shop_name
    save_owner_state(
        state["owner_id"],
        current_shop_id,
        current_shop_name,
        state.get("last_shops") or [],
        state.get("intent"),
    )
    state["steps"].append("Saved owner context")
    return state
