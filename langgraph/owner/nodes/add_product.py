"""Create product node."""

from owner import product_service
from owner import owner_backend_client
from owner.intent_requirements import (
    get_create_product_missing_fields,
    get_create_product_question,
)
from owner.nodes import backend_result_message, is_error, list_from_response, store_pending_action_if_shop_missing
from owner.nodes.product_helpers import format_money, router_payload
from owner.owner_state import OwnerChatState


def create_product_node(state: OwnerChatState) -> OwnerChatState:
    payload = router_payload(state)
    fields = _merge_create_fields(state.get("pending_product_create", {}), payload.get("fields") or {})
    create_payload = {**payload, "fields": fields}

    if not _require_selected_shop_for_create(state, fields):
        return state

    if state.get("confidence", 0.0) < 0.70:
        state["response"] = "Please clarify the product you want to add."
        state["needs_clarification"] = True
        state["steps"].append("Create product confidence too low")
        return state

    missing = get_create_product_missing_fields(create_payload)
    if missing:
        state["pending_product_create"] = fields
        state["response"] = get_create_product_question(missing[0], create_payload)
        state["needs_clarification"] = True
        state["steps"].append(f"Create product missing fields: {', '.join(missing)}")
        return state

    product_data = {
        "name": fields.get("name"),
        "description": fields.get("description"),
        "price": fields.get("price"),
        "stock": fields.get("stock"),
        "category": fields.get("category"),
        "delivery_time": fields.get("delivery_time"),
        "brand": fields.get("brand"),
        "available": fields.get("available"),
        "sizes": fields.get("sizes") or [],
        "colors": fields.get("colors") or [],
        "images": fields.get("images") or [],
    }
    result = product_service.create_product(state["selected_shop_id"], product_data)
    if is_error(result):
        state["response"] = backend_result_message(result, "Product could not be created.")
        state["steps"].append("Create product failed")
        return state

    product = result.get("product") if isinstance(result, dict) else {}
    product = product or {}
    name = product.get("name") or fields.get("name")
    price = product.get("price", fields.get("price"))
    stock = product.get("stock", fields.get("stock"))
    sizes = fields.get("sizes") or []
    details = [f"price {format_money(price, fields.get('currency'))}"]
    if fields.get("stock") is not None:
        details.append(f"stock {stock}")
    if sizes:
        details.append("sizes " + ", ".join(sizes))
    state["last_product"] = {"id": product.get("id"), "name": name, "price": price, "stock": stock}
    state["pending_product_create"] = {}
    if len(details) == 1:
        state["response"] = f"Done. I added {name} for {format_money(price, fields.get('currency'))}."
    else:
        state["response"] = f"Done. I added {name} with " + ", ".join(details) + "."
    state["steps"].append("Created product")
    return state


add_product_node = create_product_node


def _merge_create_fields(existing: dict, incoming: dict) -> dict:
    fields = dict(existing or {})
    for key, value in (incoming or {}).items():
        if key in {"sizes", "colors", "images"}:
            merged = list(fields.get(key) or [])
            for item in value or []:
                if item not in merged:
                    merged.append(item)
            fields[key] = merged
        elif value not in (None, "", [], {}):
            fields[key] = value
    if fields.get("available") is None:
        fields["available"] = True
    return fields


def _require_selected_shop_for_create(state: OwnerChatState, fields: dict) -> bool:
    if state.get("selected_shop_id") or state.get("current_shop_id"):
        return True

    state["pending_product_create"] = fields
    shops_response = owner_backend_client.get_owner_shops(state["owner_id"])
    shops = [] if is_error(shops_response) else list_from_response(shops_response, "shops")
    state["last_shops"] = shops
    if shops:
        names = [f"{index}. {shop.get('name') or shop.get('id') or shop.get('_id')}" for index, shop in enumerate(shops, start=1)]
        state["response"] = "Please select a shop first. Available shops: " + ", ".join(names) + "."
    else:
        state["response"] = "Please select a shop first."
    state["needs_clarification"] = True
    store_pending_action_if_shop_missing(state)
    state["steps"].append("Create product missing selected shop")
    return False
