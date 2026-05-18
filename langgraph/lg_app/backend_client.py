"""Backend API client used by LangGraph agent nodes."""

import os
from typing import Any

import requests


BACKEND_BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def create_order(payload: dict[str, Any]) -> dict[str, Any]:
    """Create an order through the backend order endpoint."""
    response = requests.post(
        f"{BACKEND_BASE_URL}/api/orders",
        json=payload,
        timeout=8,
    )
    response.raise_for_status()
    return response.json()


def get_orders_by_session(shop_id: str, session_id: str) -> dict[str, Any]:
    """Fetch this customer's session orders for one shop."""
    response = requests.get(
        f"{BACKEND_BASE_URL}/api/shops/{shop_id}/orders/session/{session_id}",
        timeout=8,
    )
    response.raise_for_status()
    return response.json()
