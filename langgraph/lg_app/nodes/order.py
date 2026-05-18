"""Node: Order creation agent."""

import re
from typing import Any

import requests

from lg_app import backend_client
from lg_app.state import ChatState


CUSTOMER_FIELDS = ("name", "phone", "city", "delivery_address")
KNOWN_CITIES = (
    "Casablanca",
    "Rabat",
    "Marrakech",
    "Fes",
    "Tangier",
    "Agadir",
    "Meknes",
    "Oujda",
    "Kenitra",
    "Tetouan",
    "Safi",
    "El Jadida",
    "Mohammedia",
)
QUANTITY_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def _clean(value: str) -> str:
    return value.strip(" \t\r\n.,;!?")


def _extract_labeled_fields(message: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    label_pattern = r"delivery\s+address|address|name|phone|city"
    pattern = re.compile(
        rf"\b({label_pattern})\s*:\s*(.*?)(?=\s*[,;]\s*(?:{label_pattern}|qty|quantity)\s*:|$)",
        re.IGNORECASE,
    )

    for match in pattern.finditer(message):
        label = re.sub(r"\s+", " ", match.group(1).lower())
        value = _clean(match.group(2))
        if not value:
            continue
        if label == "address":
            label = "delivery_address"
        elif label == "delivery address":
            label = "delivery_address"
        fields[label] = value

    return fields


def _extract_phone(message: str) -> str | None:
    phone_match = _phone_match(message)
    if not phone_match:
        return None
    phone = re.sub(r"\s+", " ", phone_match.group(1)).strip(" .,-")
    if len(re.sub(r"\D", "", phone)) < 8:
        return None
    return phone


def _phone_match(message: str) -> re.Match[str] | None:
    match = re.search(r"\b(?:\+?\d{1,3}[\s.-]?)?(0\d(?:[\s.-]?\d){8})\b", message)
    if match:
        return match
    return re.search(r"\b(\+?\d[\d.-]{7,}\d)\b", message)


def _extract_quantity(message: str) -> int | None:
    patterns = [
        r"\b(?:qty|quantity)\s*:?\s*(\d+)\b",
        r"\bx\s*(\d+)\b",
        r"\b(\d+)\s*x\b",
        r"\b(\d+)\s*(?:pieces?|pcs?|units?)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            quantity = int(match.group(1))
            return quantity if quantity > 0 else None

    normalized = message.lower()
    for word, quantity in QUANTITY_WORDS.items():
        if re.search(rf"\b{word}\s+(?:pieces?|pcs?|units?|items?|stuff|of them|from)\b", normalized):
            return quantity
        if re.search(rf"\b(?:qty|quantity)\s*:?\s*{word}\b", normalized):
            return quantity
    return None


def _extract_order_fields(message: str) -> dict[str, Any]:
    customer_info = _extract_labeled_fields(message)

    if "phone" not in customer_info:
        phone = _extract_phone(message)
        if phone:
            customer_info["phone"] = phone

    for city in KNOWN_CITIES:
        if city.lower() in message.lower() and "city" not in customer_info:
            customer_info["city"] = city
            break

    if "name" not in customer_info:
        name_match = re.search(
            r"\b(?:my name is|name is|i am|i'm)\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s'-]{1,60})",
            message,
            re.IGNORECASE,
        )
        if name_match:
            customer_info["name"] = _clean(name_match.group(1))

    match = _phone_match(message)
    if match and "name" not in customer_info:
        before_phone = _clean(message[: match.start()])
        before_phone = re.sub(
            r"\b(my name is|name is|i am|i'm|phone|tel|telephone)\b",
            "",
            before_phone,
            flags=re.IGNORECASE,
        ).strip(" ,.-")
        if before_phone and len(before_phone.split()) <= 4:
            customer_info["name"] = before_phone

    if match and "delivery_address" not in customer_info:
        after_phone = _clean(message[match.end():])
        if after_phone:
            customer_info["delivery_address"] = after_phone

    quantity = _extract_quantity(message)
    extracted: dict[str, Any] = {"customer_info": customer_info}
    if quantity is not None:
        extracted["quantity"] = quantity
    return extracted


def _merge_order_data(order: dict[str, Any], extracted: dict[str, Any]) -> dict[str, Any]:
    merged = dict(order)
    customer_info = dict(merged.get("customer_info") or {})
    customer_info.update(extracted.get("customer_info") or {})
    merged["customer_info"] = customer_info
    if extracted.get("quantity") is not None:
        merged["quantity"] = extracted["quantity"]
    else:
        merged.setdefault("quantity", 1)
    return merged


def _missing_customer_fields(customer_info: dict[str, str]) -> list[str]:
    return [field for field in CUSTOMER_FIELDS if not customer_info.get(field)]


def _missing_message(missing: list[str]) -> str:
    labels = {
        "name": "name",
        "phone": "phone",
        "city": "city",
        "delivery_address": "delivery address",
    }
    return "Please send " + ", ".join(labels[field] for field in missing) + "."


def _order_error(response: requests.Response | None, exc: Exception) -> str:
    if response is None:
        return "The order service is not reachable right now."

    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            detail = response.json().get("detail")
            if detail:
                return str(detail)
        except ValueError:
            pass

    text = response.text.strip()
    if text:
        return text[:240]
    return str(exc)


def order_agent(state: ChatState) -> ChatState:
    """Extract customer details and create an order through the backend."""
    if re.search(r"\b(cancel|stop|nevermind|never mind|forget it|annuler)\b", state["message"], re.IGNORECASE):
        state["pending_order_json"] = None
        state["response"] = "No problem, I cancelled the pending order details."
        state["steps"].append("Cancelled pending order")
        return state

    product_id = state.get("active_product_id")
    if not product_id:
        state["response"] = "Which product would you like to order?"
        state["steps"].append("Order missing active_product_id")
        return state

    order = _merge_order_data(
        state.get("pending_order_json") or {},
        _extract_order_fields(state["message"]),
    )
    if state.get("delivery_city"):
        order["customer_info"]["city"] = state["delivery_city"]
    if state.get("delivery_address"):
        order["customer_info"]["delivery_address"] = state["delivery_address"]

    missing = _missing_customer_fields(order["customer_info"])
    if missing:
        state["pending_order_json"] = order
        state["response"] = _missing_message(missing)
        state["steps"].append(f"Order pending missing fields: {', '.join(missing)}")
        return state

    payload = {
        "shop_id": state["shop_id"],
        "session_id": state["session_id"],
        "product_id": product_id,
        "quantity": int(order.get("quantity") or 1),
        "customer_info": {
            "name": order["customer_info"]["name"],
            "phone": order["customer_info"]["phone"],
            "city": order["customer_info"]["city"],
            "delivery_address": order["customer_info"]["delivery_address"],
        },
    }

    response = None
    try:
        backend_response = backend_client.create_order(payload)
        state["pending_order_json"] = None
        state["response"] = backend_response.get("message") or "Your order has been created successfully."
        state["steps"].append("Created order through backend")
    except requests.HTTPError as exc:
        response = exc.response
        state["response"] = f"I could not create the order: {_order_error(response, exc)}"
        state["steps"].append("Order creation failed")
    except Exception:
        state["response"] = "I have the order details, but I could not reach the order service right now."
        state["steps"].append("Order service unavailable")

    return state
