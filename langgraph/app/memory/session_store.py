"""In-memory session store for user context."""

from typing import Optional

# In-memory session storage
sessions = {}


def get_session_state(session_id: str) -> dict:
    """
    Retrieve session state.
    
    Args:
        session_id: User session identifier
        
    Returns:
        dict with keys: active_product, last_intent
    """
    if session_id not in sessions:
        sessions[session_id] = {
            "active_product": None,
            "last_intent": None
        }
    return sessions[session_id]


def save_session_state(
    session_id: str,
    active_product: Optional[str] = None,
    last_intent: Optional[str] = None
) -> None:
    """
    Save session state.
    
    Args:
        session_id: User session identifier
        active_product: Currently active product name
        last_intent: Last detected intent
    """
    if session_id not in sessions:
        sessions[session_id] = {}
    
    if active_product is not None:
        sessions[session_id]["active_product"] = active_product
    if last_intent is not None:
        sessions[session_id]["last_intent"] = last_intent
