"""Pending flow resolution for owner-agent conversations."""

import re
from typing import Any

from owner.intent_requirements import get_create_product_missing_fields
from owner.owner_state import OwnerChatState


def resolve_pending_flow(state: OwnerChatState, router_result: dict) -> dict:
    pending_create = state.get("pending_product_create") or {}
    if not pending_create:
        return router_result

    new_intent = router_result.get("intent")
    confidence = float(router_result.get("confidence") or 0)
    if new_intent == "select_shop" and not (state.get("selected_shop_id") or state.get("current_shop_id")):
        return router_result

    explicit_switch = _looks_like_different_request(state["message"])

    if not explicit_switch:
        followup_result = build_create_followup_result(state["message"], pending_create)
        if followup_result:
            state["steps"].append("Continuing pending product create")
            return followup_result

    if new_intent not in {"unknown", "create_product"} and confidence >= 0.75:
        state["pending_product_create"] = {}
        state["steps"].append(f"Cancelled pending create due to new intent: {new_intent}")
        return router_result

    if explicit_switch:
        state["steps"].append("Paused pending product create")
        return router_result

    followup_result = build_create_followup_result(state["message"], pending_create)
    if followup_result:
        state["steps"].append("Continuing pending product create")
        return followup_result

    return router_result


def build_create_followup_result(message: str, pending_create: dict) -> dict | None:
    output = _empty_create_output()
    _extract_create_fields(message, output)

    missing = get_create_product_missing_fields({"fields": pending_create})
    fields = output["fields"]
    if "name" in missing and not fields.get("name") and fields.get("price") is None:
        name = message.strip(" ,.")
        if name and not _is_generic_product_name(name):
            fields["name"] = name
            output["product_reference"] = name
            _add_known_color(fields, name)

    if not _has_extracted_fields(fields):
        return None

    output["missing_fields"] = get_create_product_missing_fields(output)
    return output


def _empty_create_output() -> dict[str, Any]:
    return {
        "intent": "create_product",
        "product_reference": None,
        "action": "create_product",
        "fields": {
            "name": None,
            "description": None,
            "price": None,
            "currency": None,
            "stock": None,
            "sizes": [],
            "colors": [],
            "category": None,
            "delivery_time": None,
            "brand": None,
            "available": True,
            "images": [],
            "shop_query": None,
            "status": None,
            "order_id": None,
        },
        "stock_operation": {"type": None, "quantity": None},
        "language": "english",
        "confidence": 0.95,
        "requires_confirmation": False,
        "missing_fields": [],
        "notes": None,
    }


def _extract_create_fields(message: str, output: dict) -> None:
    fields = output["fields"]
    explicit_called = re.search(
        r"(?:create|add|new product)\s+(?:a\s+|an\s+|new\s+)?product\s+(?:called|named)\s+(.+?)(?=\s+(?:for|price|at)\s+\d|\s+\d+(?:\.\d+)?\s*(?:dh|mad|usd|eur|€|\$)\b|\s+stock\b|\s+sizes?\b|\s+colors?\b|\s+category\b|$)",
        message,
        re.IGNORECASE,
    )
    name_match = explicit_called or re.search(
        r"(?:add|create|new product)\s+(?:a\s+|an\s+|product\s+)?(.+?)(?=\s+(?:for|price|at)\s+\d|\s+\d+(?:\.\d+)?\s*(?:dh|mad|usd|eur|€|\$)\b|\s+stock\b|\s+sizes?\b|\s+colors?\b|\s+category\b|$)",
        message,
        re.IGNORECASE,
    )
    if not name_match:
        name_match = re.search(
            r"\b(?:name(?:\s+of\s+(?:the\s+)?product)?|product\s+name)\s+(?:is|:)\s+(.+?)(?=\s+(?:and\s+)?(?:price|stock|sizes?|colors?|category)\b|$)",
            message,
            re.IGNORECASE,
        )
    if name_match:
        name = name_match.group(1).strip(" ,.")
        if explicit_called or not _is_generic_product_name(name):
            fields["name"] = name
            output["product_reference"] = name
            _add_known_color(fields, name)

    price_match = re.search(r"(?:for|price|at)\s+(?:is\s+|:)?(\d+(?:\.\d+)?)\s*(dh|mad|usd|eur|€|\$)?", message, re.IGNORECASE)
    if not price_match:
        price_match = re.search(r"^\s*(\d+(?:\.\d+)?)\s*(dh|mad|usd|eur|€|\$)\b", message, re.IGNORECASE)
    if price_match:
        fields["price"] = float(price_match.group(1))
        fields["currency"] = price_match.group(2) or None

    stock_match = re.search(r"\bstock\s+(\d+)\b", message, re.IGNORECASE)
    if stock_match:
        fields["stock"] = int(stock_match.group(1))
        output["stock_operation"] = {"type": "set", "quantity": fields["stock"]}

    sizes_match = re.search(r"\bsizes?\s+(.+?)(?=\s+stock\b|\s+colors?\b|\s+category\b|$)", message, re.IGNORECASE)
    if sizes_match:
        fields["sizes"] = _split_values(sizes_match.group(1))

    colors_match = re.search(r"\bcolors?\s+(.+?)(?=\s+stock\b|\s+sizes?\b|\s+category\b|$)", message, re.IGNORECASE)
    if colors_match:
        fields["colors"] = _split_values(colors_match.group(1))

    category_match = re.search(r"\bcategory\s+(.+?)(?=\s+price\b|\s+stock\b|\s+sizes?\b|\s+colors?\b|$)", message, re.IGNORECASE)
    if category_match:
        fields["category"] = category_match.group(1).strip(" ,.")


def _looks_like_different_request(message: str) -> bool:
    lower = message.lower().strip()
    return bool(
        re.match(
            r"^(?:show|list|get|find|delete|remove|rename|make|mark|change|update|set|increase|decrease|add\s+\d+\s+units?)\b",
            lower,
        )
        or re.match(r"^please\b", lower)
        or ("product" in lower and re.search(r"\b(?:which|what|show|list)\b", lower))
    )


def _has_extracted_fields(fields: dict) -> bool:
    return any(
        value not in (None, "", [], {})
        for key, value in fields.items()
        if key not in {"available"}
    )


def _split_values(value: str) -> list[str]:
    return [item.strip(" ,.") for item in re.split(r"[,/ ]+", value) if item.strip(" ,.")]


def _is_generic_product_name(name: str) -> bool:
    normalized = " ".join(name.lower().strip().split())
    return normalized in {
        "product",
        "products",
        "some product",
        "some products",
        "a product",
        "new product",
        "new products",
        "new product here",
        "new products here",
        "product here",
        "products here",
        "item",
        "some item",
    }


def _add_known_color(fields: dict, name: str) -> None:
    colors = ["black", "white", "red", "blue", "green", "yellow", "pink", "purple", "grey", "gray", "brown"]
    words = set(name.lower().split())
    color = next((candidate for candidate in colors if candidate in words), None)
    if color and color not in fields["colors"]:
        fields["colors"].append(color)
