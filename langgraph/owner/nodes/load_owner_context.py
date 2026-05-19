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
    state["steps"].append("Loaded owner context")
    return state
