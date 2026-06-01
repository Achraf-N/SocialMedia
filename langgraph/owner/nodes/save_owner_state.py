"""Persist owner state after each turn."""

from owner.owner_memory import save_owner_state
from owner.owner_state import OwnerChatState
from owner.nodes import apply_response_prefix


def save_owner_state_node(state: OwnerChatState) -> OwnerChatState:
    apply_response_prefix(state)
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
        state.get("pending_confirmation") or {},
        state.get("pending_product_create") or {},
        state.get("pending_action"),
        state.get("pending_field"),
        state.get("last_product") or {},
        state.get("last_products") or [],
    )
    state["steps"].append("Saved owner context")
    return state
