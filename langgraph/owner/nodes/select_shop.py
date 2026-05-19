"""Select active owner shop."""

from owner import owner_backend_client
from owner.nodes import error_message, is_error, list_from_response
from owner.owner_state import OwnerChatState


def _matches(shop: dict, query: str) -> bool:
    query = query.lower().strip()
    return query in {
        str(shop.get("id") or "").lower(),
        str(shop.get("_id") or "").lower(),
        str(shop.get("name") or "").lower(),
    } or query in str(shop.get("name") or "").lower()


def select_shop_node(state: OwnerChatState) -> OwnerChatState:
    query = state.get("extracted_data", {}).get("shop_query") or state["message"]
    data = owner_backend_client.get_owner_shops(state["owner_id"])
    if is_error(data):
        state["response"] = error_message(data)
        state["steps"].append("Select shop failed")
        return state

    shops = list_from_response(data, "shops")
    selected = next((shop for shop in shops if _matches(shop, query)), None)
    if not selected:
        names = [str(shop.get("name") or shop.get("id") or shop.get("_id")) for shop in shops]
        suffix = " Available shops: " + ", ".join(names) + "." if names else ""
        state["response"] = "Which shop would you like to manage?" + suffix
        state["needs_clarification"] = True
        state["steps"].append("Shop selection unclear")
        return state

    state["selected_shop_id"] = str(selected.get("id") or selected.get("_id"))
    state["selected_shop_name"] = str(selected.get("name") or state["selected_shop_id"])
    state["current_shop_id"] = state["selected_shop_id"]
    state["current_shop_name"] = state["selected_shop_name"]
    state["response"] = f"Selected shop: {state['selected_shop_name']}."
    state["steps"].append("Selected owner shop")
    return state
