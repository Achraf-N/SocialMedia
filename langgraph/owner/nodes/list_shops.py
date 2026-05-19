"""List owner shops."""

from owner import owner_backend_client
from owner.nodes import error_message, is_error, list_from_response
from owner.owner_state import OwnerChatState


def list_shops_node(state: OwnerChatState) -> OwnerChatState:
    data = owner_backend_client.get_owner_shops(state["owner_id"])
    if is_error(data):
        state["response"] = error_message(data)
        state["steps"].append("List shops failed")
        return state

    shops = list_from_response(data, "shops")
    if not shops:
        state["response"] = "You do not have any shops yet."
    else:
        lines = [f"{shop.get('name') or 'Unnamed shop'} ({shop.get('id') or shop.get('_id')})" for shop in shops]
        state["response"] = "Your shops: " + "; ".join(lines)
    state["steps"].append("Listed owner shops")
    return state
