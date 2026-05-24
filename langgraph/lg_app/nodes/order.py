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
ORDINAL_WORDS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
}


def _clean(value: str) -> str:
    return value.strip(" \t\r\n.,;!?")


def _product_id(product: dict[str, Any]) -> str | None:
    value = product.get("id") or product.get("_id")
    return str(value) if value is not None else None


def _quantity_from_token(value: str) -> int | None:
    value = value.lower().strip()
    if value.isdigit():
        quantity = int(value)
        return quantity if quantity > 0 else None
    return QUANTITY_WORDS.get(value)


def _catalog_product_by_position(state: ChatState, position: int) -> dict[str, Any] | None:
    catalog = state.get("last_catalog_products") or []
    if position < 1 or position > len(catalog):
        return None

    product_name = catalog[position - 1]
    for product in state.get("shop_data") or []:
        if product.get("name") == product_name:
            return product
    return None


def _product_aliases(product: dict[str, Any]) -> list[str]:
    name = str(product.get("name") or "").lower()
    aliases = {name}
    tokens = re.findall(r"[a-z0-9]+", name)
    for token in tokens:
        if len(token) >= 4:
            aliases.add(token)
        if len(token) >= 5:
            aliases.add(token[:3])
    return sorted((alias for alias in aliases if alias), key=len, reverse=True)


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
        r"\b(?:order|buy|purchase|reserve|get|take|need|want)\s+(?:to\s+)?(?:order|buy|purchase|get|take)?\s*(\d+)\b",
        r"\bx\s*(\d+)\b",
        r"\b(\d+)\s*x\b",
        r"\b(\d+)\s*(?:pieces?|pcs?|units?|products?|items?)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            quantity = int(match.group(1))
            return quantity if quantity > 0 else None

    normalized = message.lower()
    for word, quantity in QUANTITY_WORDS.items():
        if re.search(
            rf"\b(?:order|buy|purchase|reserve|get|take|need|want)\s+"
            rf"(?:to\s+)?(?:order|buy|purchase|get|take)?\s*{word}\b",
            normalized,
        ):
            return quantity
        if re.search(rf"\b{word}\s+(?:pieces?|pcs?|units?|products?|items?|stuff|of them|from)\b", normalized):
            return quantity
        if re.search(rf"\b(?:qty|quantity)\s*:?\s*{word}\b", normalized):
            return quantity
    return None


def _wants_multiple_distinct_products(message: str) -> bool:
    normalized = message.lower()
    quantity_word_pattern = "|".join(QUANTITY_WORDS)
    return bool(
        re.search(rf"\b(?:\d+|{quantity_word_pattern})\s+different\s+products?\b", normalized)
        or re.search(rf"\b(?:these|those|the|first|both)\s+(?:\d+|{quantity_word_pattern})?\s*(?:different\s+)?products?\b", normalized)
        or re.search(r"\b(?:all|both)\s+(?:of\s+)?(?:them|these|those|products?)\b", normalized)
    )


def _extract_catalog_position_items(state: ChatState) -> list[dict[str, Any]]:
    message = state["message"].lower()
    quantity_pattern = r"\d+|" + "|".join(QUANTITY_WORDS)
    ordinal_pattern = r"\d+|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth"
    patterns = [
        rf"\b>?\s*(?P<qty>{quantity_pattern})\s*(?:items?|pieces?|pcs?|units?)?\s*(?:for|of|on|in|from)?\s*(?:the\s+)?(?:product\s*)?(?P<pos>{ordinal_pattern})(?:st|nd|rd|th)?\s*(?:products?|one)?\b",
        rf"\b(?:product\s*)?(?P<pos>{ordinal_pattern})(?:st|nd|rd|th)?\s*(?:products?|one)?\s*(?:x|qty|quantity|:|=|for|of|on|in)?\s*>?\s*(?P<qty>{quantity_pattern})\b",
    ]
    items_by_id: dict[str, dict[str, Any]] = {}
    for pattern in patterns:
        for match in re.finditer(pattern, message):
            quantity = _quantity_from_token(match.group("qty"))
            pos_value = match.group("pos")
            position = int(pos_value) if pos_value.isdigit() else ORDINAL_WORDS.get(pos_value)
            if not quantity or not position:
                continue

            product = _catalog_product_by_position(state, position)
            if not product:
                continue
            product_id = _product_id(product)
            if not product_id:
                continue
            items_by_id[product_id] = {"product_id": product_id, "quantity": quantity}

    return list(items_by_id.values())


def _extract_mentioned_items(state: ChatState, quantity: int | None) -> list[dict[str, Any]]:
    """Build order items from explicitly mentioned products or recent catalog references."""
    message = state["message"].lower()
    products = state.get("shop_data") or []
    items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    catalog_position_items = _extract_catalog_position_items(state)
    if len(catalog_position_items) > 1:
        return catalog_position_items

    quantity_pattern = r"\d+|" + "|".join(QUANTITY_WORDS)
    for product in products:
        product_id = _product_id(product)
        product_name = str(product.get("name") or "")
        if not product_id or not product_name:
            continue
        for alias in _product_aliases(product):
            match = re.search(
                rf"\b(?:(?P<qty>{quantity_pattern})\s+)?{re.escape(alias)}\b",
                message,
            )
            if match and product_id not in seen_ids:
                item_quantity = _quantity_from_token(match.group("qty") or "1") or 1
                items.append({"product_id": product_id, "quantity": item_quantity})
                seen_ids.add(product_id)
                break
        if product_name.lower() in message and product_id not in seen_ids:
            items.append({"product_id": product_id, "quantity": 1})
            seen_ids.add(product_id)

    catalog = state.get("last_catalog_products") or []
    catalog_count = quantity or len(catalog)
    references_catalog = (
        bool(catalog)
        and (
            _wants_multiple_distinct_products(message)
            or re.search(
                r"\b(?:these|those|all|the|first|both)\s+(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)?\s*(?:different\s+)?products?\b",
                message,
            )
        )
    )
    if references_catalog:
        products_by_name = {str(product.get("name")): product for product in products}
        for product_name in catalog[:catalog_count]:
            product = products_by_name.get(product_name)
            if not product:
                continue
            product_id = _product_id(product)
            if product_id and product_id not in seen_ids:
                items.append({"product_id": product_id, "quantity": 1})
                seen_ids.add(product_id)

    if len(items) > 1:
        return items
    return []


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
    if extracted.get("items"):
        merged["items"] = extracted["items"]
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


def _is_yes(message: str) -> bool:
    return bool(re.search(r"\b(yes|yeah|yep|correct|right|ok|okay|confirm|confirmed|sure|oui|ah|iwa)\b", message, re.IGNORECASE))


def _is_no(message: str) -> bool:
    return bool(re.search(r"\b(no|nope|not correct|wrong|change|different|la|non)\b", message, re.IGNORECASE))


def _latest_session_customer_info(state: ChatState) -> dict[str, str] | None:
    try:
        data = backend_client.get_orders_by_session(state["shop_id"], state["session_id"])
    except Exception:
        return None

    orders = data.get("orders", []) if isinstance(data, dict) else data
    if not orders:
        return None

    customer_info = orders[0].get("customer_info") or {}
    if _missing_customer_fields(customer_info):
        return None
    return {field: customer_info[field] for field in CUSTOMER_FIELDS}


def _customer_info_confirmation_message(customer_info: dict[str, str]) -> str:
    return (
        "I found your previous delivery details: "
        f"name {customer_info['name']}, phone {customer_info['phone']}, "
        f"city {customer_info['city']}, address {customer_info['delivery_address']}. "
        "Is this still correct?"
    )


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

    pending_order = state.get("pending_order_json") or {}
    if pending_order.get("confirm_customer_info"):
        if _is_no(state["message"]):
            pending_order["customer_info"] = {}
            pending_order.pop("confirm_customer_info", None)
            pending_order["customer_info_declined"] = True
            state["pending_order_json"] = pending_order
            state["response"] = _missing_message(list(CUSTOMER_FIELDS))
            state["steps"].append("Previous customer info declined")
            return state

        extracted_for_confirmation = _extract_order_fields(state["message"])
        if any(extracted_for_confirmation.get("customer_info", {}).values()):
            pending_order.pop("confirm_customer_info", None)
        elif _is_yes(state["message"]):
            pending_order.pop("confirm_customer_info", None)
            state["pending_order_json"] = pending_order
        else:
            state["pending_order_json"] = pending_order
            state["response"] = _customer_info_confirmation_message(pending_order["customer_info"])
            state["steps"].append("Awaiting previous customer info confirmation")
            return state

    extracted = _extract_order_fields(state["message"])
    extracted["items"] = _extract_mentioned_items(state, extracted.get("quantity"))
    order = _merge_order_data(
        state.get("pending_order_json") or {},
        extracted,
    )

    product_id = state.get("active_product_id")
    wants_distinct_products = _wants_multiple_distinct_products(state["message"])
    if wants_distinct_products and not order.get("items"):
        state["pending_order_json"] = order
        quantity = int(order.get("quantity") or 2)
        state["response"] = f"Which {quantity} products would you like to order?"
        state["steps"].append("Order missing multiple product selection")
        return state

    if not product_id and not order.get("items"):
        state["response"] = "Which product would you like to order?"
        state["steps"].append("Order missing product selection")
        return state
    if state.get("delivery_city"):
        order["customer_info"]["city"] = state["delivery_city"]
    if state.get("delivery_address"):
        order["customer_info"]["delivery_address"] = state["delivery_address"]

    missing = _missing_customer_fields(order["customer_info"])
    if missing:
        if not order.get("customer_info_declined"):
            previous_customer_info = _latest_session_customer_info(state)
            if previous_customer_info:
                order["customer_info"] = previous_customer_info
                order["confirm_customer_info"] = True
                state["pending_order_json"] = order
                state["response"] = _customer_info_confirmation_message(previous_customer_info)
                state["steps"].append("Asked to confirm previous customer info")
                return state

        state["pending_order_json"] = order
        state["response"] = _missing_message(missing)
        state["steps"].append(f"Order pending missing fields: {', '.join(missing)}")
        return state

    payload = {
        "shop_id": state["shop_id"],
        "session_id": state["session_id"],
        "customer_info": {
            "name": order["customer_info"]["name"],
            "phone": order["customer_info"]["phone"],
            "city": order["customer_info"]["city"],
            "delivery_address": order["customer_info"]["delivery_address"],
        },
    }
    if order.get("items"):
        payload["items"] = order["items"]
    else:
        payload["product_id"] = product_id
        payload["quantity"] = int(order.get("quantity") or 1)

    response = None
    try:
        backend_response = backend_client.create_order(payload)
        state["pending_order_json"] = None
        state["response"] = backend_response.get("message") or "Your order has been created successfully."
        if backend_response.get("total_price") is not None:
            state["response"] = f"{state['response']} Total: {backend_response['total_price']} MAD."
        state["steps"].append("Created order through backend")
    except requests.HTTPError as exc:
        response = exc.response
        state["response"] = f"I could not create the order: {_order_error(response, exc)}"
        state["steps"].append("Order creation failed")
    except Exception:
        state["response"] = "I have the order details, but I could not reach the order service right now."
        state["steps"].append("Order service unavailable")

    return state
