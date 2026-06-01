"""Update product price node."""

from owner import product_service
from owner.nodes import backend_result_message, is_error
from owner.nodes.product_helpers import (
    format_money,
    pop_matching_confirmation,
    product_id,
    product_name,
    resolve_single_product,
    router_payload,
    set_pending_confirmation,
)
from owner.owner_state import OwnerChatState


def update_price_node(state: OwnerChatState) -> OwnerChatState:
    pending = pop_matching_confirmation(state, "update_price")
    if pending:
        payload = pending.get("payload") or {}
        fields = payload.get("fields") or {}
        result = product_service.update_price(
            pending["shop_id"],
            pending["product_id"],
            fields.get("price"),
            fields.get("currency"),
        )
        return _finish_price_update(state, result, pending.get("product_name"), fields)

    payload = router_payload(state)
    if state.get("confidence", 0.0) < 0.70:
        state["response"] = "Please clarify the price change."
        state["needs_clarification"] = True
        return state
    fields = payload.get("fields") or {}
    if fields.get("price") is None:
        state["response"] = "Please specify the new price."
        state["needs_clarification"] = True
        return state

    product = resolve_single_product(state)
    if not product:
        return state

    old_price = float(product.get("price") or 0)
    new_price = float(fields["price"])
    if old_price > 0 and abs(new_price - old_price) / old_price > 0.5:
        set_pending_confirmation(
            state,
            "update_price",
            product,
            payload,
            f"Please confirm: change {product_name(product)} price from {format_money(old_price, fields.get('currency'))} to {format_money(new_price, fields.get('currency'))}?",
        )
        state["steps"].append("Price update requires confirmation")
        return state

    result = product_service.update_price(state["selected_shop_id"], product_id(product), new_price, fields.get("currency"))
    return _finish_price_update(state, result, product_name(product), fields)


def _finish_price_update(state: OwnerChatState, result: dict, name: str | None, fields: dict) -> OwnerChatState:
    if is_error(result):
        state["response"] = backend_result_message(result, "Price could not be updated.")
        state["steps"].append("Update price failed")
        return state
    product = result.get("product") if isinstance(result, dict) else {}
    product = product or {}
    display_name = name or product.get("name") or "the product"
    price = product.get("price", fields.get("price"))
    state["last_product"] = {
        "id": product.get("id"),
        "name": product.get("name") or display_name,
        "price": price,
        "stock": product.get("stock"),
    }
    state["response"] = f"Done. The {display_name} price is now {format_money(price, fields.get('currency'))}."
    state["steps"].append("Updated price")
    return state
