"""Persistent session store for user context."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# In-memory session storage
sessions = {}
SESSION_FILE = Path(__file__).resolve().parents[2] / ".chat_sessions.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_collection():
    """Use backend MongoDB when this module runs inside the backend app."""
    try:
        from app.core.database import chat_sessions_collection

        return chat_sessions_collection
    except Exception:
        return None


def _file_key(session_id: str, shop_id: Optional[str]) -> str:
    return f"{shop_id or ''}:{session_id}"


def _load_file_sessions() -> dict:
    if not SESSION_FILE.exists():
        return {}
    try:
        return json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_file_sessions(data: dict) -> None:
    SESSION_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def get_session_state(session_id: str, shop_id: Optional[str] = None) -> dict:
    """
    Retrieve session state.
    
    Args:
        session_id: User session identifier
        
    Returns:
        dict with keys: active_product, last_intent
    """
    default_state = {
        "active_product": None,
        "active_product_id": None,
        "active_product_name": None,
        "current_product_id": None,
        "current_product_name": None,
        "last_intent": None,
        "extracted_city": None,
        "extracted_address": None,
        "pending_order_json": None,
        "last_catalog_products": None,
    }

    collection = _get_collection()
    if collection is not None:
        record = collection.find_one({"session_id": session_id, "shop_id": shop_id})
        if record:
            return {**default_state, **record}

    file_sessions = _load_file_sessions()
    file_state = file_sessions.get(_file_key(session_id, shop_id))
    if file_state:
        return {**default_state, **file_state}

    if session_id not in sessions:
        sessions[session_id] = default_state.copy()
    return sessions[session_id]


def save_session_state(
    session_id: str,
    shop_id: Optional[str] = None,
    active_product: Optional[str] = None,
    active_product_id: Optional[str] = None,
    active_product_name: Optional[str] = None,
    current_product_id: Optional[str] = None,
    current_product_name: Optional[str] = None,
    last_intent: Optional[str] = None,
    extracted_city: Optional[str] = None,
    extracted_address: Optional[str] = None,
    pending_order_json: Optional[dict] = None,
    last_catalog_products: Optional[list[str]] = None,
    clear_pending_order: bool = False,
) -> None:
    """
    Save session state.
    
    Args:
        session_id: User session identifier
        active_product: Currently active product name
        last_intent: Last detected intent
    """
    existing = get_session_state(session_id, shop_id)
    updates = {
        "session_id": session_id,
        "shop_id": shop_id,
        "updated_at": _now(),
    }
    resolved_product_id = active_product_id or current_product_id
    resolved_product_name = active_product_name or current_product_name or active_product

    field_updates = {
        "active_product": active_product,
        "active_product_id": resolved_product_id,
        "active_product_name": resolved_product_name,
        "current_product_id": resolved_product_id,
        "current_product_name": resolved_product_name,
        "last_intent": last_intent,
        "extracted_city": extracted_city,
        "extracted_address": extracted_address,
        "last_catalog_products": last_catalog_products,
    }
    if clear_pending_order:
        field_updates["pending_order_json"] = None
    elif pending_order_json is not None:
        field_updates["pending_order_json"] = pending_order_json

    for key, value in field_updates.items():
        if value is not None:
            updates[key] = value
        elif key == "pending_order_json" and clear_pending_order:
            updates[key] = None

    merged = {**existing, **updates}
    sessions[session_id] = merged

    collection = _get_collection()
    if collection is not None:
        collection.update_one(
            {"session_id": session_id, "shop_id": shop_id},
            {
                "$set": updates,
                "$setOnInsert": {"created_at": _now()},
            },
            upsert=True,
        )
        return

    file_sessions = _load_file_sessions()
    file_sessions[_file_key(session_id, shop_id)] = {
        key: value for key, value in merged.items() if key != "_id"
    }
    _save_file_sessions(file_sessions)
