"""Owner-agent intent router with structured product extraction."""

import json
import re
from typing import Any

from owner.owner_state import OwnerChatState
from owner.pending_flow import resolve_pending_flow
from owner.prompts.router_prompt import OWNER_ROUTER_SYSTEM_PROMPT, OWNER_ROUTER_USER_PROMPT_TEMPLATE


PRODUCT_INTENTS = {
    "create_product",
    "update_product",
    "delete_product",
    "list_products",
    "get_product",
    "update_stock",
    "update_price",
    "mark_unavailable",
    "unknown",
}
NON_PRODUCT_INTENTS = {
    "greeting",
    "list_shops",
    "select_shop",
    "shop_summary",
    "list_orders",
    "update_order_status",
    "help",
}
VALID_INTENTS = PRODUCT_INTENTS | NON_PRODUCT_INTENTS
VALID_STATUSES = {"pending", "confirmed", "processing", "shipped", "delivered", "cancelled"}
PRODUCT_FIELD_WORDS = {
    "description",
    "price",
    "stock",
    "availability",
    "category",
    "brand",
    "delivery time",
    "variants",
    "variant",
    "size",
    "sizes",
    "color",
    "colors",
}


def empty_router_output() -> dict[str, Any]:
    return {
        "intent": "unknown",
        "product_reference": None,
        "action": None,
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
            "available": None,
            "images": [],
            "shop_query": None,
            "status": None,
            "order_id": None,
        },
        "stock_operation": {"type": None, "quantity": None},
        "language": "unknown",
        "confidence": 0.0,
        "requires_confirmation": False,
        "missing_fields": [],
        "notes": None,
    }


def _contains(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _parse_router_json(response_text: str) -> dict | None:
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _normalize_router_output(result: dict | None) -> dict | None:
    if not isinstance(result, dict):
        return None

    output = empty_router_output()
    intent = result.get("intent")
    if intent == "add_product":
        intent = "create_product"
    if intent not in VALID_INTENTS:
        return None
    output["intent"] = intent
    output["action"] = result.get("action") or (intent if intent in PRODUCT_INTENTS and intent != "unknown" else None)
    output["product_reference"] = _clean_scalar(result.get("product_reference"))

    fields = result.get("fields") or result.get("extracted_data") or {}
    if isinstance(fields, dict):
        for key in output["fields"]:
            value = fields.get(key)
            if key in {"sizes", "colors", "images"}:
                output["fields"][key] = _clean_list(value)
            elif key in {"price"}:
                output["fields"][key] = _to_float(value)
            elif key == "stock":
                output["fields"][key] = _to_int(value)
            else:
                output["fields"][key] = value if value not in ("", "null", "None") else None

    stock_operation = result.get("stock_operation") or {}
    if isinstance(stock_operation, dict):
        op_type = stock_operation.get("type")
        output["stock_operation"]["type"] = op_type if op_type in {"set", "increment", "decrement", None} else None
        output["stock_operation"]["quantity"] = _to_int(stock_operation.get("quantity"))

    output["language"] = result.get("language") or "unknown"
    output["confidence"] = _clamp_float(result.get("confidence"), default=0.85)
    output["requires_confirmation"] = bool(result.get("requires_confirmation", False))
    output["missing_fields"] = _clean_list(result.get("missing_fields"))
    output["notes"] = _clean_scalar(result.get("notes"))
    return _validate_missing_fields(output)


def build_owner_router_prompt(state: OwnerChatState) -> tuple[str, str]:
    user_prompt = OWNER_ROUTER_USER_PROMPT_TEMPLATE.format(
        message=state["message"],
        selected_shop_id=state.get("selected_shop_id") or "None",
        selected_shop_name=state.get("selected_shop_name") or "None",
        last_intent=state.get("intent") or state.get("extracted_data", {}).get("last_intent") or "None",
        last_product=json.dumps(state.get("last_product") or {}, ensure_ascii=False),
    )
    return OWNER_ROUTER_SYSTEM_PROMPT, user_prompt


def route_with_llm(state: OwnerChatState, use_llm: bool = False) -> dict | None:
    if not use_llm:
        return None
    try:
        from owner.llm import get_llm

        system_prompt, user_prompt = build_owner_router_prompt(state)
        response_text = get_llm().generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.0,
            max_tokens=512,
        )
        return _normalize_router_output(_parse_router_json(response_text))
    except Exception:
        return None


def deterministic_owner_router(state: OwnerChatState) -> dict:
    text = state["message"].strip()
    lower = text.lower()
    output = empty_router_output()
    output["language"] = _detect_language(lower)
    output["confidence"] = 0.95

    if _is_confirmation(lower):
        pending = state.get("pending_confirmation") or {}
        if pending:
            output["intent"] = pending.get("intent", "unknown")
            output["action"] = "confirm"
            output["product_reference"] = pending.get("product_reference")
            return output

    pending_shop_selection = _route_pending_shop_selection(text, lower, state)
    if pending_shop_selection:
        return pending_shop_selection

    known_shop_selection = _route_known_shop_selection(text, lower, state)
    if known_shop_selection:
        return known_shop_selection

    non_product = _route_non_product(text, lower)
    if non_product:
        return non_product

    product_output = _route_product_message(text, lower, state)
    if product_output["intent"] == "unknown":
        product_output["confidence"] = 0.4
    return _validate_missing_fields(product_output)


def owner_router(state: OwnerChatState) -> OwnerChatState:
    deterministic_result = deterministic_owner_router(state)
    router_result = route_with_llm(state, use_llm=True)
    if router_result is None:
        router_result = deterministic_result
        state["steps"].append("Owner router used deterministic fallback")
    elif deterministic_result.get("action") == "confirm" and (state.get("pending_confirmation") or {}):
        router_result = deterministic_result
        state["steps"].append("Owner router used deterministic confirmation guard")
    elif _should_use_deterministic_guard(router_result, deterministic_result):
        router_result = deterministic_result
        state["steps"].append("Owner router used deterministic guardrail")
    elif router_result["intent"] == "unknown" and deterministic_result["intent"] != "unknown":
        router_result = deterministic_result
        state["steps"].append("Owner router used deterministic fallback after LLM unknown")
    else:
        state["steps"].append("Owner router used local LLM")

    router_result = resolve_pending_flow(state, router_result)
    state["router_output"] = router_result
    state["intent"] = router_result["intent"]
    state["confidence"] = router_result["confidence"]
    state["extracted_data"] = {
        **state.get("extracted_data", {}),
        "owner_router": router_result,
        "product_reference": router_result.get("product_reference"),
        **{
            key: value
            for key, value in (router_result.get("fields") or {}).items()
            if key in {"shop_query", "status", "order_id"} and value
        },
    }
    state["steps"].append(f"Owner router intent: {state['intent']}")
    return state


def _should_use_deterministic_guard(router_result: dict, deterministic_result: dict) -> bool:
    deterministic_intent = deterministic_result.get("intent")
    router_intent = router_result.get("intent")
    if deterministic_intent in {"unknown", router_intent}:
        return False
    return deterministic_intent in {
        "create_product",
        "delete_product",
        "get_product",
        "select_shop",
        "update_product",
        "update_price",
        "update_stock",
        "mark_unavailable",
    }


def _route_non_product(text: str, lower: str) -> dict | None:
    extracted = {}
    intent = None
    if re.search(r"\b(?:hello|hi|salam|hey)\b", lower):
        intent = "greeting"
    elif _contains(lower, ["help", "what can you do", "how can you help me"]):
        intent = "help"
    elif _contains(lower, ["show my shops", "show shops", "list my shops", "list shops", "what shops do i have", "my stores", "my shops"]):
        intent = "list_shops"
    elif _contains(lower, ["select ", "use shop ", "choose shop ", "switch to ", "work on this shop", "choose shop id"]):
        intent = "select_shop"
        extracted["shop_query"] = re.sub(
            r"^(select|use shop|choose shop|switch to|work on|choose shop id)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
    elif _contains(lower, ["shop summary", "shop overview", "how is my shop doing", "business overview"]):
        intent = "shop_summary"
    elif _contains(lower, ["mark order", "set order", "cancel order", "update order status"]):
        intent = "update_order_status"
        extracted["order_id"] = _extract_order_id(text)
        extracted["status"] = _extract_status(lower)
    elif _contains(lower, ["show pending orders", "show orders", "what orders do i have", "orders today", "pending orders"]):
        intent = "list_orders"
        status = _extract_status(lower)
        if status:
            extracted["status"] = status

    if not intent:
        return None
    output = empty_router_output()
    output["intent"] = intent
    output["confidence"] = 0.95
    output["language"] = _detect_language(lower)
    output["fields"].update(extracted)
    return output


def _route_pending_shop_selection(text: str, lower: str, state: OwnerChatState) -> dict | None:
    if not state.get("pending_product_create"):
        return None
    return _route_known_shop_selection(text, lower, state)


def _route_known_shop_selection(text: str, lower: str, state: OwnerChatState) -> dict | None:
    if state.get("selected_shop_id") or state.get("current_shop_id"):
        return None

    shops = state.get("last_shops") or []
    if not shops:
        return None

    normalized = lower.strip(" .")
    for index, shop in enumerate(shops, start=1):
        shop_name = str(shop.get("name") or "").lower().strip()
        shop_id = str(shop.get("id") or shop.get("_id") or "").lower().strip()
        if normalized in {str(index), shop_name, shop_id} or (shop_name and (normalized in shop_name or shop_name in normalized)):
            output = empty_router_output()
            output["intent"] = "select_shop"
            output["confidence"] = 0.95
            output["language"] = _detect_language(lower)
            output["fields"]["shop_query"] = text.strip(" .")
            return output
    return None


def _route_product_message(text: str, lower: str, state: OwnerChatState) -> dict:
    output = empty_router_output()
    output["language"] = _detect_language(lower)
    output["confidence"] = 0.9

    if _contains(
        lower,
        [
            "show products",
            "list products",
            "show me all products",
            "all products",
            "what are my products",
            "my products",
            "what products do i have",
            "inventory",
            "stock list",
            "current product",
            "current products",
        ],
    ):
        output["intent"] = "list_products"
        output["action"] = "list_products"
        return output
    if "out of stock" in lower and ("which" in lower or "show" in lower or "list" in lower):
        output["intent"] = "list_products"
        output["action"] = "list_products"
        output["fields"]["stock"] = 0
        return output

    field_followup = _route_active_product_field_followup(text, lower, state)
    if field_followup:
        return field_followup

    if (
        lower.startswith(("add ", "create ", "new product"))
        or re.search(r"\b(?:add|create)\s+(?:a\s+|some\s+|new\s+)?products?\b", lower)
        or re.search(r"\bneed\s+(?:to\s+)?add\s+(?:a\s+|some\s+|new\s+)?products?\b", lower)
        or " add a " in f" {lower} "
    ) and not re.match(r"add\s+\d+\s+units?", lower):
        output["intent"] = "create_product"
        output["action"] = "create_product"
        _extract_create_fields(text, output)
        return output

    if lower.startswith("delete ") or lower.startswith("remove product ") or " delete " in f" {lower} ":
        output["intent"] = "delete_product"
        output["action"] = "delete_product"
        output["product_reference"] = _extract_reference(
            text,
            [r"(?:delete|remove product|remove)\s+(?:the\s+)?(.+)$"],
            state,
        )
        output["requires_confirmation"] = True
        output["notes"] = "Deletion requires confirmation."
        return output

    if "unavailable" in lower or "out of stock" in lower:
        output["intent"] = "mark_unavailable"
        output["action"] = "mark_unavailable"
        output["product_reference"] = _extract_reference(
            text,
            [r"make\s+(?:the\s+)?(.+?)\s+unavailable", r"mark\s+(?:the\s+)?(.+?)\s+unavailable", r"(.+?)\s+is\s+out\s+of\s+stock"],
            state,
        )
        output["fields"]["available"] = False
        return output

    if _is_price_lookup(lower):
        output["intent"] = "get_product"
        output["action"] = "get_product"
        output["product_reference"] = _extract_reference(
            text,
            [
                r"(?:what\s+is|what's|show|tell\s+me)\s+(?:the\s+)?(?:price|cost)\s+of\s+(.+)$",
                r"(?:how\s+much\s+(?:is|for)|how\s+much\s+does)\s+(.+?)(?:\s+cost)?$",
                r"(?:price|cost)\s+(?:of|for)\s+(.+)$",
            ],
            state,
        )
        return output

    price_match = None
    if "price" in lower:
        price_match = re.search(r"(?:change|set|update)\s+(?:the\s+)?(?:price\s+of\s+)?(.+?)\s+(?:price\s+)?to\s+(\d+(?:\.\d+)?)\s*([A-Za-z]+)?", text, re.IGNORECASE)
    if price_match:
        output["intent"] = "update_price"
        output["action"] = "update_price"
        output["product_reference"] = _clean_reference(price_match.group(1), state)
        output["fields"]["price"] = float(price_match.group(2))
        output["fields"]["currency"] = price_match.group(3) or None
        return output

    stock_patterns = [
        (r"(?:update|set|change)\s+(?:stock\s+of\s+)?(.+?)\s+(?:stock\s+)?to\s+(\d+)", "set"),
        (r"add\s+(\d+)\s+units?\s+to\s+(?:the\s+)?(.+)", "increment"),
        (r"(?:increase|add)\s+(?:the\s+)?(.+?)\s+stock\s+by\s+(\d+)", "increment"),
        (r"(?:decrease|remove|subtract)\s+(?:the\s+)?(.+?)\s+stock\s+by\s+(\d+)", "decrement"),
    ]
    for pattern, operation in stock_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        output["intent"] = "update_stock"
        output["action"] = "update_stock"
        if operation == "increment" and pattern.startswith("add"):
            output["stock_operation"] = {"type": operation, "quantity": int(match.group(1))}
            output["product_reference"] = _clean_reference(match.group(2), state)
        else:
            output["product_reference"] = _clean_reference(match.group(1), state)
            output["stock_operation"] = {"type": operation, "quantity": int(match.group(2))}
        return output

    rename_match = re.search(r"rename\s+(?:the\s+)?(.+?)\s+to\s+(.+)$", text, re.IGNORECASE)
    if rename_match:
        output["intent"] = "update_product"
        output["action"] = "update_product"
        output["product_reference"] = _clean_reference(rename_match.group(1), state)
        output["fields"]["name"] = rename_match.group(2).strip(" .")
        return output

    if lower.startswith(("show ", "get ", "find ")):
        output["intent"] = "get_product"
        output["action"] = "get_product"
        output["product_reference"] = _extract_reference(text, [r"(?:show|get|find)\s+(?:the\s+)?(.+)$"], state)
        return output

    return output


def _route_active_product_field_followup(text: str, lower: str, state: OwnerChatState) -> dict | None:
    last_product = state.get("last_product") or {}
    if not last_product.get("id"):
        return None
    if re.search(r"\b(?:add|create)\s+(?:a\s+|an\s+|new\s+)?products?\b", lower) or lower.startswith("new product"):
        return None

    field = _mentioned_product_field(lower)
    if not field:
        return None
    if not re.search(r"\b(?:also|add|update|set|change)\b", lower):
        return None
    if field != "description" and re.search(r"\b(?:of|for)\s+(?!it\b|this\b|that\b)[A-Za-z0-9]", text, re.IGNORECASE):
        return None

    output = empty_router_output()
    output["intent"] = "update_product"
    output["action"] = "update_product"
    output["language"] = _detect_language(lower)
    output["confidence"] = 0.95
    output["product_id"] = last_product.get("id")
    output["product_reference"] = last_product.get("name") or last_product.get("id")

    if field == "description":
        description = _extract_inline_description(text)
        if description:
            output["fields"]["description"] = description
        else:
            output["awaiting_field"] = "description"
    elif field == "price":
        price_match = re.search(r"(\d+(?:\.\d+)?)\s*(dh|mad|usd|eur|€|\$)?", text, re.IGNORECASE)
        if price_match:
            output["intent"] = "update_price"
            output["action"] = "update_price"
            output["fields"]["price"] = float(price_match.group(1))
            output["fields"]["currency"] = price_match.group(2) or None
        else:
            output["awaiting_field"] = "price"
    elif field == "stock":
        stock_match = re.search(r"(\d+)", text)
        if stock_match:
            output["intent"] = "update_stock"
            output["action"] = "update_stock"
            output["stock_operation"] = {"type": "set", "quantity": int(stock_match.group(1))}
        else:
            output["awaiting_field"] = "stock"
    elif field in {"color", "size", "variants"}:
        output["awaiting_field"] = field
    else:
        output["awaiting_field"] = field

    return _validate_missing_fields(output)


def _mentioned_product_field(lower: str) -> str | None:
    for field in sorted(PRODUCT_FIELD_WORDS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(field)}\b", lower):
            if field in {"colors", "color"}:
                return "color"
            if field in {"sizes", "size"}:
                return "size"
            if field in {"variant", "variants"}:
                return "variants"
            return field
    return None


def _extract_inline_description(text: str) -> str | None:
    match = re.search(r"\bdescription\s*(?:is|:|to)\s+(.+)$", text, re.IGNORECASE)
    if not match:
        match = re.search(r"\b(?:add|update|set|change)\s+(?:a\s+)?description\s+(.+)$", text, re.IGNORECASE)
    if not match:
        return None
    value = match.group(1).strip(" .")
    return value or None


def _extract_create_fields(text: str, output: dict) -> None:
    explicit_new_product = re.search(
        r"\bcreate\s+new\s+product\s+(.+?)(?=\s+(?:for|price|at)\s+\d|\s+\d+(?:\.\d+)?\s*(?:dh|mad|usd|eur|€|\$)\b|\s+stock\b|\s+sizes?\b|\s+colors?\b|\s+category\b|$)",
        text,
        re.IGNORECASE,
    )
    explicit_called = re.search(
        r"(?:create|add|new product)\s+(?:a\s+|an\s+|new\s+)?product\s+(?:called|named)\s+(.+?)(?=\s+(?:for|price|at)\s+\d|\s+\d+(?:\.\d+)?\s*(?:dh|mad|usd|eur|€|\$)\b|\s+stock\b|\s+sizes?\b|\s+colors?\b|\s+category\b|$)",
        text,
        re.IGNORECASE,
    )
    name_match = explicit_called or explicit_new_product or re.search(r"(?:add|create|new product)\s+(?:a\s+|an\s+|product\s+)?(.+?)(?=\s+(?:for|price|at)\s+\d|\s+\d+(?:\.\d+)?\s*(?:dh|mad|usd|eur|€|\$)\b|\s+stock\b|\s+sizes?\b|\s+colors?\b|\s+category\b|$)", text, re.IGNORECASE)
    if name_match:
        name = name_match.group(1).strip(" ,.")
        if explicit_called or explicit_new_product or not _is_generic_product_name(name):
            output["fields"]["name"] = name
            output["product_reference"] = name

    _extract_create_detail_fields(text, output)
    color = _known_color(output["fields"]["name"] or "")
    if color and color not in output["fields"]["colors"]:
        output["fields"]["colors"].append(color)
    output["fields"]["available"] = True


def _extract_create_detail_fields(text: str, output: dict) -> None:
    name_match = re.search(r"\b(?:name(?:\s+of\s+(?:the\s+)?product)?|product\s+name)\s+(?:is|:)\s+(.+?)(?=\s+(?:and\s+)?(?:price|stock|sizes?|colors?|category)\b|$)", text, re.IGNORECASE)
    if name_match:
        name = name_match.group(1).strip(" ,.")
        if not _is_generic_product_name(name):
            output["fields"]["name"] = name
            output["product_reference"] = name

    price_match = re.search(r"(?:for|price|at)\s+(?:is\s+|:)?(\d+(?:\.\d+)?)\s*(dh|mad|usd|eur|€|\$)?", text, re.IGNORECASE)
    if not price_match:
        price_match = re.search(r"^(?:add|create|new product)\s+(?:a\s+|an\s+|product\s+)?.+?\s+(\d+(?:\.\d+)?)\s*(dh|mad|usd|eur|€|\$)", text, re.IGNORECASE)
    if not price_match:
        price_match = re.search(r"^\s*(\d+(?:\.\d+)?)\s*(dh|mad|usd|eur|€|\$)\b", text, re.IGNORECASE)
    if price_match:
        output["fields"]["price"] = float(price_match.group(1))
        output["fields"]["currency"] = price_match.group(2) or None
    stock_match = re.search(r"\bstock\s+(\d+)\b", text, re.IGNORECASE)
    if stock_match:
        stock = int(stock_match.group(1))
        output["fields"]["stock"] = stock
        output["stock_operation"] = {"type": "set", "quantity": stock}
    sizes_match = re.search(r"\bsizes?\s+(.+?)(?=\s+stock\b|\s+colors?\b|\s+category\b|$)", text, re.IGNORECASE)
    if sizes_match:
        output["fields"]["sizes"] = _split_values(sizes_match.group(1))
    colors_match = re.search(r"\bcolors?\s+(.+?)(?=\s+stock\b|\s+sizes?\b|\s+category\b|$)", text, re.IGNORECASE)
    if colors_match:
        output["fields"]["colors"] = _split_values(colors_match.group(1))
    category_match = re.search(r"\bcategory\s+(.+?)(?=\s+price\b|\s+stock\b|\s+sizes?\b|\s+colors?\b|$)", text, re.IGNORECASE)
    if category_match:
        output["fields"]["category"] = category_match.group(1).strip(" ,.")
    description_match = re.search(r"\bdescription\s+(.+?)(?=\s+price\b|\s+stock\b|\s+sizes?\b|\s+colors?\b|\s+category\b|\s+brand\b|\s+delivery\s+time\b|$)", text, re.IGNORECASE)
    if description_match:
        output["fields"]["description"] = description_match.group(1).strip(" ,.")
    brand_match = re.search(r"\bbrand\s+(.+?)(?=\s+price\b|\s+stock\b|\s+sizes?\b|\s+colors?\b|\s+category\b|\s+description\b|\s+delivery\s+time\b|$)", text, re.IGNORECASE)
    if brand_match:
        output["fields"]["brand"] = brand_match.group(1).strip(" ,.")
    delivery_match = re.search(r"\bdelivery\s+time\s+(.+?)(?=\s+price\b|\s+stock\b|\s+sizes?\b|\s+colors?\b|\s+category\b|\s+description\b|\s+brand\b|$)", text, re.IGNORECASE)
    if delivery_match:
        output["fields"]["delivery_time"] = delivery_match.group(1).strip(" ,.")


def _validate_missing_fields(output: dict) -> dict:
    missing = set(output.get("missing_fields") or [])
    fields = output.get("fields") or {}
    if output["intent"] == "create_product":
        if not fields.get("name"):
            missing.add("name")
        if fields.get("price") is None:
            missing.add("price")
    elif output["intent"] in {"update_price"} and fields.get("price") is None:
        missing.add("price")
    elif output["intent"] in {"delete_product", "get_product", "update_stock", "update_price", "update_product", "mark_unavailable"}:
        if not output.get("product_reference"):
            missing.add("product_reference")
    output["missing_fields"] = sorted(missing)
    return output


def _extract_status(text: str) -> str | None:
    for status in VALID_STATUSES:
        if status in text:
            return status
    if "cancel order" in text or text.startswith("cancel "):
        return "cancelled"
    return None


def _extract_order_id(message: str) -> str | None:
    match = re.search(r"\border\s+([A-Za-z0-9_-]+)\b", message, re.IGNORECASE)
    return match.group(1) if match else None


def _extract_reference(text: str, patterns: list[str], state: OwnerChatState) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _clean_reference(match.group(1), state)
    return None


def _is_price_lookup(lower: str) -> bool:
    if re.search(r"\b(?:change|set|update)\b", lower):
        return False
    return bool(
        re.search(r"\b(?:what(?:\s+is|'s)|show|tell\s+me)\s+(?:the\s+)?(?:price|cost)\s+of\b", lower)
        or re.search(r"\bhow\s+much\s+(?:is|for|does)\b", lower)
        or re.search(r"\b(?:price|cost)\s+(?:of|for)\b", lower)
    )


def _clean_reference(value: str | None, state: OwnerChatState) -> str | None:
    value = _clean_scalar(value)
    if not value:
        return None
    value = re.sub(r"^\s*[-:]\s*", "", value).strip()
    value = re.sub(r"\s+(?:permanently|please)$", "", value, flags=re.IGNORECASE).strip(" ,.")
    value = re.sub(r"^(?:the|a|an)\s+", "", value, flags=re.IGNORECASE).strip(" ,.")
    if value.lower() in {"it", "this", "that"}:
        last_product = state.get("last_product") or {}
        return last_product.get("name") or value.lower()
    return value


def _clean_scalar(value: Any) -> str | None:
    if value in (None, "", "null", "None"):
        return None
    return str(value).strip()


def _clean_list(value: Any) -> list:
    if not value:
        return []
    if isinstance(value, list):
        return [item for item in value if item not in (None, "", "null", "None")]
    return _split_values(str(value))


def _split_values(value: str) -> list[str]:
    return [item.strip(" ,.") for item in re.split(r"[,/ ]+", value) if item.strip(" ,.")]


def _to_float(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "", "null", "None") else None
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    try:
        return int(float(value)) if value not in (None, "", "null", "None") else None
    except (TypeError, ValueError):
        return None


def _clamp_float(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(number, 1.0))


def _known_color(name: str) -> str | None:
    colors = ["black", "white", "red", "blue", "green", "yellow", "pink", "purple", "grey", "gray", "brown"]
    words = set(name.lower().split())
    return next((color for color in colors if color in words), None)


def _is_generic_product_name(name: str) -> bool:
    normalized = " ".join(name.lower().strip().split())
    if normalized in PRODUCT_FIELD_WORDS:
        return True
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


def _detect_language(text: str) -> str:
    if re.search(r"[\u0600-\u06FF]", text):
        return "arabic"
    if any(word in text for word in ["wach", "bghit", "dir", "safi"]):
        return "darija"
    if any(word in text for word in ["bonjour", "prix", "produit", "supprimer"]):
        return "french"
    if any(word in text for word in ["preis", "produkt", "löschen"]):
        return "german"
    return "english"


def _is_confirmation(text: str) -> bool:
    return text.strip().lower() in {"yes", "y", "confirm", "confirmed", "ok", "okay", "do it", "go ahead"}
