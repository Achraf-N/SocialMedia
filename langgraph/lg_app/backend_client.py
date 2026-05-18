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
