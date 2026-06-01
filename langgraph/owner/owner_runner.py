"""Runner for local owner-agent testing."""

from owner.owner_graph import get_owner_graph
from owner.owner_state import OwnerChatState


def run_owner_chat(owner_id: str, message: str) -> dict:
    initial_state: OwnerChatState = {
        "owner_id": owner_id,
        "message": message,
        "selected_shop_id": None,
        "selected_shop_name": None,
        "current_shop_id": None,
        "current_shop_name": None,
        "last_shops": [],
        "intent": None,
        "response": None,
        "steps": [],
        "extracted_data": {},
        "router_output": {},
        "pending_confirmation": {},
        "pending_product_create": {},
        "pending_action": None,
        "pending_field": None,
        "response_prefix": None,
        "last_product": {},
        "last_products": [],
        "confidence": 0.0,
        "needs_clarification": False,
    }
    final_state = get_owner_graph().invoke(initial_state)
    return {
        "response": final_state["response"],
        "intent": final_state["intent"],
        "selected_shop_id": final_state["selected_shop_id"],
        "selected_shop_name": final_state["selected_shop_name"],
        "current_shop_id": final_state.get("current_shop_id"),
        "current_shop_name": final_state.get("current_shop_name"),
        "steps": final_state["steps"],
        "pending_action": final_state.get("pending_action"),
        "pending_field": final_state.get("pending_field"),
    }
