"""In-memory owner agent session store."""

from typing import Optional


owner_sessions: dict[str, dict] = {}


def get_owner_state(owner_id: str) -> dict:
    """Return persisted owner context."""
    if owner_id not in owner_sessions:
        owner_sessions[owner_id] = {
            "selected_shop_id": None,
            "selected_shop_name": None,
            "last_intent": None,
        }
    return owner_sessions[owner_id]


def save_owner_state(
    owner_id: str,
    selected_shop_id: Optional[str],
    selected_shop_name: Optional[str],
    last_intent: Optional[str],
) -> None:
    """Persist owner context."""
    owner_sessions[owner_id] = {
        "selected_shop_id": selected_shop_id,
        "selected_shop_name": selected_shop_name,
        "last_intent": last_intent,
    }
