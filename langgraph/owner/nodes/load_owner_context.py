"""Load owner memory into state."""

from owner.owner_memory import get_owner_state
from owner.owner_state import OwnerChatState


def load_owner_context(state: OwnerChatState) -> OwnerChatState:
    saved = get_owner_state(state["owner_id"])
    state["selected_shop_id"] = saved.get("selected_shop_id")
    state["selected_shop_name"] = saved.get("selected_shop_name")
    state["steps"].append("Loaded owner context")
    return state
