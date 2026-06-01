"""Load owner memory into state."""

from owner.owner_memory import get_owner_state
from owner.owner_state import OwnerChatState


def load_owner_context(state: OwnerChatState) -> OwnerChatState:
    saved = get_owner_state(state["owner_id"])
    current_shop_id = saved.get("current_shop_id") or saved.get("selected_shop_id")
    current_shop_name = saved.get("current_shop_name") or saved.get("selected_shop_name")
    state["selected_shop_id"] = current_shop_id
    state["selected_shop_name"] = current_shop_name
    state["current_shop_id"] = current_shop_id
    state["current_shop_name"] = current_shop_name
    state["last_shops"] = saved.get("last_shops") or []
    state["extracted_data"] = {
        **state.get("extracted_data", {}),
        "last_intent": saved.get("last_intent"),
    }
    state["pending_confirmation"] = saved.get("pending_confirmation") or {}
    state["pending_product_create"] = saved.get("pending_product_create") or {}
    state["pending_action"] = saved.get("pending_action")
    state["pending_field"] = saved.get("pending_field")
    state["response_prefix"] = None
    state["last_product"] = saved.get("last_product") or {}
    state["last_products"] = saved.get("last_products") or []
    state["steps"].append("Loaded owner context")
    return state
