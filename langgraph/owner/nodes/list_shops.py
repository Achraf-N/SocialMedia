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
    state["last_shops"] = shops
    if not shops:
        state["response"] = "You do not have any shops yet."
    else:
        lines = [
            f"{index}. {shop.get('name') or 'Unnamed shop'}"
            for index, shop in enumerate(shops, start=1)
        ]
        state["response"] = "Your shops: " + "; ".join(lines)
    state["steps"].append("Listed owner shops")
    return state
