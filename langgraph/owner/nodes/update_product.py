"""Update product metadata node."""

from owner import product_service
from owner.nodes import backend_result_message, is_error
from owner.nodes.product_helpers import product_id, product_name, resolve_single_product, router_payload
from owner.owner_state import OwnerChatState


UPDATABLE_FIELDS = {"name", "description", "category", "available", "sizes", "colors", "images"}


def update_product_node(state: OwnerChatState) -> OwnerChatState:
    payload = router_payload(state)
    if state.get("confidence", 0.0) < 0.70:
        state["response"] = "Please clarify the product update."
        state["needs_clarification"] = True
        return state

    product = resolve_single_product(state)
    if not product:
        return state

    awaiting_field = payload.get("awaiting_field")
    if awaiting_field == "description":
        state["pending_field"] = {
            "intent": "update_product",
            "field": "description",
            "target": {
                "type": "product",
                "id": product_id(product),
                "name": product_name(product),
            },
        }
        state["response"] = f"Sure. Send me the description for {product_name(product)}."
        state["needs_clarification"] = True
        state["steps"].append("Awaiting product description")
        return state

    fields = {
        key: value
        for key, value in (payload.get("fields") or {}).items()
        if key in UPDATABLE_FIELDS and value not in (None, "", [], {})
    }
    if not fields:
        state["response"] = "Please specify what to update."
        state["needs_clarification"] = True
        state["steps"].append("Update product missing fields")
        return state

    result = product_service.update_product(state["selected_shop_id"], product_id(product), fields)
    if is_error(result):
        state["response"] = backend_result_message(result, "Product could not be updated.")
        state["steps"].append("Update product failed")
        return state

    updated = result.get("product") if isinstance(result, dict) else {}
    updated = updated or {}
    state["last_product"] = {
        "id": updated.get("id"),
        "name": updated.get("name") or fields.get("name") or product_name(product),
        "price": updated.get("price"),
        "stock": updated.get("stock"),
    }
    state["response"] = f"Done. Updated {state['last_product']['name']}."
    if set(fields) == {"description"}:
        state["response"] = f"Done. I updated the description for {state['last_product']['name']}."
    state["steps"].append("Updated product")
    return state
