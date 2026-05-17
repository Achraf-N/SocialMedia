"""Node: Order intent agent."""

import os
import re

import requests

from lg_app.state import ChatState


BACKEND_BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def _active_product(state: ChatState) -> dict | None:
    for product in state.get("shop_data", []):
        if product.get("name") == state.get("active_product"):
            return product
    return None


def _extract_order_fields(message: str) -> dict:
    fields: dict = {}
    phone_match = re.search(r"(\+?\d[\d\s.-]{7,}\d)", message)
    if phone_match:
        fields["customer_phone"] = re.sub(r"\s+", " ", phone_match.group(1)).strip()

    quantity_match = re.search(r"\b(?:qty|quantity|x)\s*(\d+)\b|\b(\d+)\s*(?:pieces?|pcs?|units?)\b", message, re.IGNORECASE)
    if quantity_match:
        fields["quantity"] = int(quantity_match.group(1) or quantity_match.group(2))

    name_match = re.search(r"\b(?:my name is|name is|i am|i'm)\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s'-]{1,60})", message, re.IGNORECASE)
    if name_match:
        fields["customer_name"] = name_match.group(1).strip(" .?!")

    payment_match = re.search(r"\b(cash on delivery|cash|card|bank transfer|transfer|paypal)\b", message, re.IGNORECASE)
    if payment_match:
        fields["payment_method"] = payment_match.group(1).lower()

    address_match = re.search(r"\b(?:my address is|address is|deliver(?: it)? to|send(?: it)? to)\s+(.+)", message, re.IGNORECASE)
    if address_match:
        fields["address"] = address_match.group(1).strip(" .?!")

    return fields


def _missing_fields(order: dict) -> list[str]:
    required = ["customer_name", "customer_phone", "city", "address", "quantity"]
    return [field for field in required if not order.get(field)]


def _missing_message(missing: list[str], product_name: str) -> str:
    labels = {
        "customer_name": "your name",
        "customer_phone": "your phone number",
        "city": "your city",
        "address": "your delivery address",
        "quantity": "the quantity",
    }
    wanted = ", ".join(labels[field] for field in missing)
    return f"I can help you order {product_name}. Please send {wanted}."


def order_agent(state: ChatState) -> ChatState:
    """Collect order details and create an order only when required fields exist."""
    product = _active_product(state)
    if not product:
        state["response"] = "Which product would you like to order?"
        state["steps"].append("Order missing product clarification")
        return state

    if product.get("available") is not True or product.get("stock", 0) <= 0:
        state["response"] = f"{product['name']} is not available right now, so I cannot create an order for it."
        state["pending_order_json"] = None
        state["steps"].append("Order blocked because product unavailable")
        return state

    order = state.get("pending_order_json") or {}
    order.update(_extract_order_fields(state["message"]))
    order.setdefault("product_id", product.get("id") or product.get("_id"))
    order.setdefault("quantity", 1)
    if state.get("delivery_city"):
        order["city"] = state["delivery_city"]
    if state.get("delivery_address"):
        order["address"] = state["delivery_address"]

    missing = _missing_fields(order)
    if missing:
        state["pending_order_json"] = order
        state["response"] = _missing_message(missing, product["name"])
        state["steps"].append(f"Order pending missing fields: {', '.join(missing)}")
        return state

    try:
        response = requests.post(
            f"{BACKEND_BASE_URL}/api/shops/{state['shop_id']}/orders/public",
            json=order,
            timeout=8,
        )
        response.raise_for_status()
        created = response.json()
        state["pending_order_json"] = None
        state["response"] = (
            f"Your order is created. Order ID: {created['order_id']}. "
            f"Status: {created['status']}. Total: {created['total_price']} MAD."
        )
        state["steps"].append(f"Created order: {created['order_id']}")
    except requests.HTTPError as exc:
        detail = response.text if "response" in locals() else str(exc)
        state["response"] = f"I could not create the order: {detail}"
        state["steps"].append("Order creation failed")
    except Exception as exc:
        state["response"] = f"I have the order details, but I could not reach the order service: {exc}"
        state["steps"].append("Order service unavailable")

    return state
