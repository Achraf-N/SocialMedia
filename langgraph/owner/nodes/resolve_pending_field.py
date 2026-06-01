"""Resolve answers to a previously requested field value."""

from owner.owner_state import OwnerChatState


def resolve_pending_field_node(state: OwnerChatState) -> OwnerChatState:
    pending = state.get("pending_field")
    if not pending:
        return state

    target = pending.get("target") or {}
    field = pending.get("field")
    intent = pending.get("intent")
    if intent != "update_product" or field != "description" or not target.get("id"):
        return state

    description = state["message"].strip()
    state["intent"] = "update_product"
    state["router_output"] = {
        "intent": "update_product",
        "product_reference": target.get("name") or target.get("id"),
        "product_id": target.get("id"),
        "action": "update_product",
        "fields": {"description": description},
        "stock_operation": {"type": None, "quantity": None},
        "language": "unknown",
        "confidence": 0.95,
        "requires_confirmation": False,
        "missing_fields": [],
        "notes": None,
    }
    state["extracted_data"] = {
        **(state.get("extracted_data") or {}),
        "owner_router": state["router_output"],
        "product_reference": state["router_output"]["product_reference"],
    }
    state["pending_field"] = None
    state["confidence"] = 0.95
    state["needs_clarification"] = False
    state["steps"].append(f"Resolved pending field: {field}")
    return state
