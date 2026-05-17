"""Node: Intent router with LLM and deterministic modes."""

import json
import re
from typing import Optional
from lg_app.state import ChatState
from lg_app.utils.product_matcher import find_product
from lg_app.llm.prompts import SYSTEM_PROMPTS, PROMPT_TEMPLATES


def _contains_word(text: str, words: list[str]) -> bool:
    """Check if text contains any of the words with word boundary checks."""
    for word in words:
        # Use word boundary regex to match whole words only
        if re.search(r'\b' + re.escape(word) + r'\b', text):
            return True
    return False


def _contains_any(text: str, phrases: list[str]) -> bool:
    """Check whether text contains any phrase."""
    return any(phrase in text for phrase in phrases)


def _extract_delivery_location(message: str) -> tuple[Optional[str], Optional[str]]:
    """Extract simple city/address details from common commerce phrasing."""
    known_cities = [
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
    ]
    lowered = message.lower()

    address_patterns = [
        r"\bmy address is\s+(.+)",
        r"\baddress is\s+(.+)",
        r"\bdeliver(?: it)? to\s+(.+)",
        r"\bsend(?: it)? to\s+(.+)",
        r"\bto\s+(.+)",
        r"\blivraison\s+(?:à|a|l)?\s*(.+)",
    ]

    address = None
    for pattern in address_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip(" .?!")
            if any(char.isdigit() for char in candidate) or "," in candidate:
                address = candidate
            break

    for city in known_cities:
        if city.lower() in lowered:
            return city, address

    patterns = [
        r"\b(?:to|in|for|à|a|l)\s+([A-Z][A-Za-zÀ-ÿ-]+(?:\s+[A-Z][A-Za-zÀ-ÿ-]+)?)",
        r"\b(?:live in|livraison à|livraison a|livraison|katsifto l|bghit livraison)\s+([A-Z][A-Za-zÀ-ÿ-]+(?:\s+[A-Z][A-Za-zÀ-ÿ-]+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            city = match.group(1).strip(" .?!,")
            return city.title(), address

    return None, address


def _parse_router_json(response_text: str) -> Optional[dict]:
    """Extract the first JSON object from an LLM response."""
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


def _resolve_product_query(product_query: Optional[str], products: list[dict]) -> Optional[str]:
    """Return an exact shop product name, or None if the query is not a product."""
    if not product_query:
        return None

    product_query = str(product_query).strip()
    if not product_query or product_query.lower() in {"none", "null"}:
        return None

    for product in products:
        name = product.get("name")
        if name and product_query.lower() == name.lower():
            return name

    matched = find_product(product_query, products)
    if matched:
        return matched["name"]

    return None


def _normalize_router_result(result: dict, products: list[dict]) -> Optional[dict]:
    """Validate and normalize LLM router output."""
    valid_intents = {
        "greeting",
        "small_talk",
        "product_list",
        "product_info_question",
        "availability_question",
        "order_intent",
        "price_question",
        "delivery_question",
        "payment_question",
        "complaint",
        "human_needed",
        "unknown",
    }

    intent = result.get("intent")
    if intent not in valid_intents:
        return None

    confidence = result.get("confidence", 0.85)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.85

    return {
        "intent": intent,
        "product_query": _resolve_product_query(result.get("product_query"), products),
        "confidence": max(0.0, min(confidence, 1.0)),
        "needs_human": bool(result.get("needs_human", False)),
    }


def _apply_sales_priority(state: ChatState, router_result: dict) -> dict:
    """Correct ambiguous LLM routing with sales-specific priority rules."""
    message = state["message"]
    msg_lower = message.lower()
    explicit_product = find_product(message, state["shop_data"])
    active_product = state.get("active_product")

    delivery_terms = [
        "delivery",
        "deliver",
        "shipping",
        "ship",
        "address",
        "city",
        "cities",
        "casablanca",
        "rabat",
        "marrakech",
        "fes",
        "tangier",
        "delivery cost",
        "delivery price",
        "delivery fee",
        "how much time",
        "how long",
        "arrive",
    ]
    payment_terms = [
        "payment",
        "pay",
        "cash on delivery",
        "cash",
        "card",
        "transfer",
        "bank transfer",
        "paypal",
    ]
    price_terms = [
        "price",
        "cost",
        "how much",
        "expensive",
        "cheap",
        "cheapest",
        "discount",
        "promo",
    ]
    availability_terms = [
        "available",
        "availability",
        "in stock",
        "stock",
        "disponible",
    ]
    order_terms = [
        "buy",
        "order",
        "purchase",
        "reserve",
        "confirm",
        "i want it",
        "take it",
        "send it to me",
        "can i buy",
    ]
    info_terms = [
        "details",
        "detail",
        "explain",
        "info",
        "information",
        "usage",
        "benefits",
        "ingredients",
        "tell me more",
        "about",
    ]

    if explicit_product:
        router_result["product_query"] = explicit_product["name"]
    elif router_result.get("product_query"):
        router_result["product_query"] = _resolve_product_query(
            router_result["product_query"],
            state["shop_data"],
        )

    is_cash_on_delivery = "cash on delivery" in msg_lower

    if state.get("pending_order_json") and _contains_any(
        msg_lower,
        ["name", "phone", "address", "city", "cash", "card", "transfer", "paypal", "quantity", "qty", "my address"],
    ):
        router_result["intent"] = "order_intent"
        router_result["confidence"] = max(router_result.get("confidence", 0.0), 0.95)
    elif _contains_any(msg_lower, delivery_terms) and not is_cash_on_delivery:
        router_result["intent"] = "delivery_question"
        router_result["confidence"] = max(router_result.get("confidence", 0.0), 0.95)
    elif _contains_any(msg_lower, payment_terms):
        router_result["intent"] = "payment_question"
        router_result["confidence"] = max(router_result.get("confidence", 0.0), 0.95)
    elif _contains_any(msg_lower, price_terms):
        router_result["intent"] = "price_question"
        router_result["confidence"] = max(router_result.get("confidence", 0.0), 0.95)
    elif _contains_any(msg_lower, availability_terms):
        router_result["intent"] = "availability_question"
        router_result["confidence"] = max(router_result.get("confidence", 0.0), 0.95)
    elif _contains_any(msg_lower, order_terms):
        router_result["intent"] = "order_intent"
        router_result["confidence"] = max(router_result.get("confidence", 0.0), 0.95)
    elif explicit_product and _contains_any(msg_lower, info_terms):
        router_result["intent"] = "product_info_question"
        router_result["confidence"] = max(router_result.get("confidence", 0.0), 0.9)

    if not router_result.get("product_query") and active_product:
        uses_context = _contains_any(
            msg_lower,
            [" it", "this", "that product", "same one", "this one", "how much", "price", "available", "stock", "deliver"],
        )
        if uses_context:
            router_result["product_query"] = active_product

    city, address = _extract_delivery_location(message)
    state["delivery_city"] = city
    state["delivery_address"] = address
    if city:
        state["steps"].append(f"Detected delivery city: {city}")
    if address:
        state["steps"].append(f"Detected delivery address: {address}")

    return router_result


def build_router_prompt(
    message: str,
    known_products: list[str],
    active_product: Optional[str] = None
) -> tuple[str, str]:
    """
    Build system and user prompts for LLM-based router.
    
    Args:
        message: Current user message
        known_products: List of available product names
        active_product: Currently active product in session
        
    Returns:
        tuple: (system_prompt, user_prompt)
    """
    system_prompt = SYSTEM_PROMPTS["router"]
    
    user_prompt = PROMPT_TEMPLATES["router"].format(
        message=message,
        known_products=json.dumps(known_products, indent=2),
        active_product=active_product if active_product else "None"
    )
    
    return system_prompt, user_prompt


def route_with_llm(
    state: ChatState,
    use_llm: bool = False
) -> dict:
    """
    LLM-based intent routing using Ollama.
    
    Args:
        state: Current chat state
        use_llm: Whether to use LLM (disabled by default)
        
    Returns:
        dict with: intent, product_query, confidence, needs_human
        or None to use deterministic routing
    """
    if not use_llm:
        return None
    
    try:
        from lg_app.llm import get_llm
        
        known_products = [p["name"] for p in state["shop_data"]]
        system_prompt, user_prompt = build_router_prompt(
            state["message"],
            known_products,
            state.get("active_product")
        )
        
        llm = get_llm()
        response_text = llm.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.0,
            max_tokens=256
        )
        
        result = _parse_router_json(response_text)
        if not result:
            return None

        return _normalize_router_result(result, state["shop_data"])
    
    except Exception as e:
        # Fallback to deterministic
        return None


def deterministic_intent_router(state: ChatState) -> dict:
    """
    Fallback: Deterministic keyword-based intent detection.
    
    Supports intents:
    - greeting
    - small_talk
    - product_list
    - product_info_question
    - price_question
    - delivery_question
    - payment_question
    - complaint
    - human_needed
    - unknown
    
    Returns:
        dict with: intent, product_query, confidence, needs_human
    """
    msg_lower = state["message"].lower()
    
    # Initialize result
    result = {
        "intent": "unknown",
        "product_query": None,
        "confidence": 0.85,  # Deterministic is less confident than LLM
        "needs_human": False
    }
    
    # Try to find a product in the message
    product = find_product(state["message"], state["shop_data"])
    if product:
        result["product_query"] = product["name"]
    
    # Delivery has priority because "how much" can mean delivery cost/time.
    if _contains_any(msg_lower, ["delivery", "deliver", "shipping", "ship", "address", "city", "cities", "delivery cost", "delivery price", "how much time", "how long", "arrive"]) and "cash on delivery" not in msg_lower:
        result["intent"] = "delivery_question"
        result["confidence"] = 0.95
    
    # Payment patterns
    elif _contains_any(msg_lower, ["payment", "pay", "cash on delivery", "cash", "card", "transfer", "bank transfer", "paypal"]):
        result["intent"] = "payment_question"
        result["product_query"] = None
        result["confidence"] = 0.95
    
    # Price patterns
    elif _contains_any(msg_lower, ["price", "cost", "how much", "expensive", "cheap", "cheapest", "discount", "promo"]):
        result["intent"] = "price_question"
        if product:
            result["product_query"] = product["name"]
        elif state.get("active_product"):
            result["product_query"] = state["active_product"]
        result["confidence"] = 0.95
    
    # Availability patterns
    elif _contains_any(msg_lower, ["available", "availability", "in stock", "stock", "disponible"]):
        result["intent"] = "availability_question"
        if product:
            result["product_query"] = product["name"]
        elif state.get("active_product"):
            result["product_query"] = state["active_product"]
        result["confidence"] = 0.95
    
    # Order intent
    elif _contains_any(msg_lower, ["buy", "order", "purchase", "reserve", "confirm", "i want it", "take it", "send it to me", "can i buy"]):
        result["intent"] = "order_intent"
        if product:
            result["product_query"] = product["name"]
        elif state.get("active_product"):
            result["product_query"] = state["active_product"]
        result["confidence"] = 0.95
    
    # Greeting patterns (use word boundary to avoid matching "hi" in "this")
    elif _contains_word(msg_lower, ["hello", "hi", "salam", "hey"]):
        result["intent"] = "greeting"
        result["confidence"] = 0.95
    
    # Small talk patterns
    elif _contains_word(msg_lower, ["thank you", "thanks", "ok", "okay", "bye", "good", "understood"]):
        result["intent"] = "small_talk"
        result["confidence"] = 0.9
    
    # Product list and catalog comparison patterns
    elif (
        _contains_word(msg_lower, ["products", "catalog", "what do you offer", "what services", "what do you sell", "available products", "what do you provide", "what can i buy"])
        or any(word in msg_lower for word in ["cheapest", "lowest price", "least expensive", "most expensive", "highest price"])
    ):
        result["intent"] = "product_list"
        result["product_query"] = None
        result["confidence"] = 0.95
    
    # Product info patterns (or product mentioned)
    elif _contains_word(msg_lower, ["details", "explain", "info", "available", "usage", "benefits", "ingredients"]) or product:
        result["intent"] = "product_info_question"
        if product:
            result["product_query"] = product["name"]
        result["confidence"] = 0.9
    
    # Complaint patterns
    elif _contains_word(msg_lower, ["refund", "problem", "angry", "late", "bad", "issue"]):
        result["intent"] = "complaint"
        result["needs_human"] = True
        result["confidence"] = 0.95
    
    # Human needed patterns
    elif _contains_word(msg_lower, ["support"]) or "order not arrived" in msg_lower:
        result["intent"] = "human_needed"
        result["needs_human"] = True
        result["confidence"] = 0.95
    
    return result


def intent_router(state: ChatState) -> ChatState:
    """
    Intent router node: Detect intent and extract product query.
    
    Supports two modes:
    1. LLM-based (TODO: implement)
    2. Deterministic (fallback/default)
    
    Updates state with:
    - intent
    - product_query
    - confidence
    - needs_human
    """
    # Try local Ollama/Qwen router first. Deterministic routing is only a fallback.
    router_result = route_with_llm(state, use_llm=True)
    
    # Fall back to deterministic if LLM not available
    if router_result is None:
        router_result = deterministic_intent_router(state)
        state["steps"].append("Router used deterministic fallback")
    else:
        state["steps"].append("Router used local LLM: qwen3:8b")

    router_result = _apply_sales_priority(state, router_result)
    
    # Update state with router results
    state["intent"] = router_result["intent"]
    state["product_query"] = router_result["product_query"]
    state["needs_human"] = router_result.get("needs_human", False)
    
    # Store confidence for debugging/analytics
    if "confidence" not in state:
        state["confidence"] = router_result.get("confidence", 0.85)
    else:
        # If confidence field exists in state, update it
        state["confidence"] = router_result.get("confidence", 0.85)
    
    state["steps"].append(
        f"Detected intent: {state['intent']} (confidence: {router_result.get('confidence', 0.85)})"
    )
    
    return state
