"""Runner for local owner-agent testing."""

from owner.owner_graph import get_owner_graph
from owner.owner_state import OwnerChatState


def run_owner_chat(owner_id: str, message: str) -> dict:
    initial_state: OwnerChatState = {
        "owner_id": owner_id,
        "message": message,
        "selected_shop_id": None,
        "selected_shop_name": None,
        "intent": None,
        "response": None,
        "steps": [],
        "extracted_data": {},
        "confidence": 0.0,
        "needs_clarification": False,
    }
    final_state = get_owner_graph().invoke(initial_state)
    return {
        "response": final_state["response"],
        "intent": final_state["intent"],
        "selected_shop_id": final_state["selected_shop_id"],
        "selected_shop_name": final_state["selected_shop_name"],
        "steps": final_state["steps"],
    }
