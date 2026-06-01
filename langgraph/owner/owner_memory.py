"""In-memory owner agent session store."""

from typing import Optional


owner_sessions: dict[str, dict] = {}


def get_owner_state(owner_id: str) -> dict:
    """Return persisted owner context."""
    if owner_id not in owner_sessions:
        owner_sessions[owner_id] = {
            "selected_shop_id": None,
            "selected_shop_name": None,
            "current_shop_id": None,
            "current_shop_name": None,
            "last_shops": [],
            "pending_confirmation": {},
            "pending_product_create": {},
            "pending_action": None,
            "pending_field": None,
            "last_product": {},
            "last_products": [],
            "last_intent": None,
        }
    return owner_sessions[owner_id]


def save_owner_state(
    owner_id: str,
    selected_shop_id: Optional[str],
    selected_shop_name: Optional[str],
    last_shops: Optional[list[dict]],
    last_intent: Optional[str],
    pending_confirmation: Optional[dict] = None,
    pending_product_create: Optional[dict] = None,
    pending_action: Optional[dict] = None,
    pending_field: Optional[dict] = None,
    last_product: Optional[dict] = None,
    last_products: Optional[list[dict]] = None,
) -> None:
    """Persist owner context."""
    current_shop_id = selected_shop_id
    current_shop_name = selected_shop_name
    owner_sessions[owner_id] = {
        "selected_shop_id": selected_shop_id,
        "selected_shop_name": selected_shop_name,
        "current_shop_id": current_shop_id,
        "current_shop_name": current_shop_name,
        "last_shops": last_shops or [],
        "pending_confirmation": pending_confirmation or {},
        "pending_product_create": pending_product_create or {},
        "pending_action": pending_action,
        "pending_field": pending_field,
        "last_product": last_product or {},
        "last_products": last_products or [],
        "last_intent": last_intent,
    }
