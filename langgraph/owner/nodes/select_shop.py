"""Select active owner shop."""

from owner import owner_backend_client
from owner.intent_requirements import get_create_product_missing_fields, get_create_product_question
from owner.nodes import error_message, is_error, list_from_response
from owner.owner_state import OwnerChatState


def _matches(shop: dict, query: str) -> bool:
    query = query.lower().strip()
    shop_id = str(shop.get("id") or "").lower()
    object_id = str(shop.get("_id") or "").lower()
    shop_name = str(shop.get("name") or "").lower()
    return query in {shop_id, object_id, shop_name} or query in shop_name or (shop_name and shop_name in query)


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
    pending_action = state.get("pending_action")
    if pending_action:
        state["intent"] = pending_action["intent"]
        state["router_output"] = pending_action.get("router_output") or state.get("router_output") or {}
        state["extracted_data"] = {
            **(state.get("extracted_data") or {}),
            **(pending_action.get("extracted_data") or {}),
        }
        state["pending_action"] = None
        state["response"] = None
        state["response_prefix"] = f"Selected shop: {state['selected_shop_name']}."
        state["needs_clarification"] = False
        state["steps"].append("Selected owner shop")
        state["steps"].append(f"Continuing pending action: {state['intent']}")
        return state

    pending_create = state.get("pending_product_create") or {}
    if pending_create:
        payload = {"fields": pending_create, "product_reference": pending_create.get("name")}
        missing = get_create_product_missing_fields(payload)
        if missing:
            state["response"] = (
                f"Selected shop: {state['selected_shop_name']}.\n\n"
                + get_create_product_question(missing[0], payload)
            )
            state["needs_clarification"] = True
        else:
            state["response"] = f"Selected shop: {state['selected_shop_name']}. Send the product details when ready."
    else:
        state["response"] = f"Selected shop: {state['selected_shop_name']}."
    state["steps"].append("Selected owner shop")
    return state
