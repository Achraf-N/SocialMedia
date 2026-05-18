"""Node: Intent router with LLM and deterministic modes."""

import json
import re
import unicodedata
from typing import Optional
from lg_app.state import ChatState
from lg_app.utils.product_matcher import find_product
from lg_app.prompts.router_prompt import ROUTER_SYSTEM_PROMPT, ROUTER_USER_PROMPT_TEMPLATE


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


def _normalize_text(text: str) -> str:
    """Lowercase and strip accents/punctuation for resilient routing checks."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9+]+", " ", ascii_text.lower()).strip()


def _is_shop_info_request(text: str) -> bool:
    """Detect questions about the shop/store itself, not a product."""
    return _contains_any(
        text,
        [
            "shop name",
            "store name",
            "business name",
            "what is the shop",
            "what is this shop",
            "what is the store",
            "about this shop",
            "about this store",
        ],
    )


def _is_catalog_request(text: str) -> bool:
    """Detect requests about the whole catalog instead of one active product."""
    return _contains_any(
        text,
        [
            "products details",
            "product details in this shop",
            "products details in this shop",
            "all product",
            "all products",
            "what products",
            "products in this shop",
            "products in this store",
            "service provided",
            "services provided",
            "what service",
            "what services",
            "what do you offer",
            "what do you sell",
            "what do you provide",
            "catalog",
            "all other product",
            "all other products",
            "other product",
            "other products",
            "price for all",
            "prices for all",
            "price of all",
            "prices of all",
            "all prices",
            "every product",
            "each product",
        ],
    )


def _is_catalog_comparison_request(text: str) -> bool:
    """Detect price/comparison requests that ask for a catalog item, not active product."""
    return _contains_any(
        text,
        [
            "expensive one",
            "most expensive",
            "highest price",
            "premium one",
            "cheapest one",
            "cheap one",
            "lowest price",
            "least expensive",
            "budget one",
        ],
    )


def _catalog_filter_field(text: str, products: list[dict]) -> Optional[str]:
    """Return brand/category name if the message references a product group."""
    for product in products:
        for key in ("brand", "category"):
            value = product.get(key)
            if value and _normalize_text(str(value)) in text:
                return str(value)
    return None


def _product_from_catalog_index(text: str, state: ChatState) -> Optional[str]:
    """Resolve references like product 1 / first product from last catalog response."""
    catalog = state.get("last_catalog_products") or []
    if not catalog:
        return None

    match = re.search(r"\bproduct\s*(\d+)\b", text)
    if match:
        index = int(match.group(1)) - 1
        if 0 <= index < len(catalog):
            return catalog[index]

    ordinal_map = {
        "first product": 0,
        "first one": 0,
        "the first": 0,
        "the first one": 0,
        "second product": 1,
        "second one": 1,
        "the second": 1,
        "the second one": 1,
        "third product": 2,
        "third one": 2,
        "the third": 2,
        "the third one": 2,
        "fourth product": 3,
        "fourth one": 3,
        "the fourth": 3,
        "the fourth one": 3,
        "1st product": 0,
        "1st one": 0,
        "2nd product": 1,
        "2nd one": 1,
        "3rd product": 2,
        "3rd one": 2,
        "4th product": 3,
        "4th one": 3,
    }
    for phrase, index in ordinal_map.items():
        if phrase in text and 0 <= index < len(catalog):
            return catalog[index]

    return None


def _is_pending_order_field_reply(text: str, has_city: bool) -> bool:
    """Detect replies that are likely filling missing order fields."""
    if has_city:
        return True
    if re.search(r"\+?\d[\d\s.-]{7,}\d", text):
        return True
    return _contains_any(
        text,
        [
            "name",
            "phone",
            "telephone",
            "address",
            "adresse",
            "city",
            "ville",
            "cash",
            "card",
            "transfer",
            "paypal",
            "quantity",
            "qty",
            "my address",
        ],
    )


def _is_order_creation_signal(message: str, normalized: str) -> bool:
    """Detect messages that should go directly to order creation."""
    if re.search(r"\b(?:name|phone|city|delivery\s+address|address)\s*:", message, re.IGNORECASE):
        return True
    return _contains_any(
        normalized,
        [
            "i want to order",
            "i want to buy",
            "place order",
            "confirm order",
            "checkout",
        ],
    )


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
            if _normalize_text(candidate) in {
                "this shop",
                "this store",
                "the shop",
                "the store",
                "all other products",
                "all products",
                "other products",
            }:
                continue
            if _normalize_text(candidate).startswith(("order ", "buy ", "purchase ", "reserve ")):
                continue
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
            if _normalize_text(city) in {
                "this shop",
                "this store",
                "the shop",
                "the store",
                "all other",
                "all other products",
                "all products",
                "other products",
                "delivery",
                "order",
                "order the",
                "buy it",
                "order it",
                "buy it",
            }:
                continue
            if _normalize_text(city).startswith(("order ", "buy ", "purchase ", "reserve ")):
                continue
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
        "shop_info_question",
        "availability_question",
        "order_intent",
        "order_creation",
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
    msg_norm = _normalize_text(message)
    explicit_product = find_product(message, state["shop_data"])
    indexed_product = _product_from_catalog_index(msg_norm, state)
    active_product = state.get("active_product")
    is_shop_info_request = _is_shop_info_request(msg_norm)
    is_catalog_request = _is_catalog_request(msg_norm) or _is_catalog_comparison_request(msg_norm)
    catalog_filter = _catalog_filter_field(msg_norm, state["shop_data"])
    if catalog_filter and not explicit_product:
        is_catalog_request = True
        state["catalog_filter"] = catalog_filter
    city, address = _extract_delivery_location(message)
    state["delivery_city"] = city
    state["delivery_address"] = address

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
        "livraison",
        "katsifto",
        "tsifto",
        "sifto",
        "bghit livraison",
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
        "paiement",
        "payer",
        "virement",
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
        "prix",
        "combien",
        "ch7al",
        "chhal",
        "taman",
        "tamane",
    ]
    availability_terms = [
        "available",
        "availability",
        "in stock",
        "stock",
        "disponible",
        "kayn",
        "kayna",
        "mawjod",
        "mawjoude",
    ]
    order_terms = [
        "i want to order",
        "i want to buy",
        "place order",
        "confirm order",
        "checkout",
        "buy",
        "order",
        "purchase",
        "reserve",
        "confirm",
        "i want it",
        "take it",
        "send it to me",
        "can i buy",
        "bghit",
        "ncommandi",
        "commander",
        "commande",
        "acheter",
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
    greeting_terms = ["hello", "hi", "salam", "slm", "hey", "bonjour", "slt", "salut"]
    small_talk_terms = [
        "thank you",
        "thanks",
        "ok",
        "okay",
        "bye",
        "good",
        "understood",
        "merci",
        "chokran",
        "shokran",
        "la",
        "non",
    ]

    if indexed_product:
        router_result["product_query"] = indexed_product
    elif is_shop_info_request or is_catalog_request:
        router_result["product_query"] = None
    elif explicit_product:
        router_result["product_query"] = explicit_product["name"]
    elif router_result.get("product_query"):
        router_result["product_query"] = _resolve_product_query(
            router_result["product_query"],
            state["shop_data"],
        )

    is_cash_on_delivery = "cash on delivery" in msg_lower

    if is_shop_info_request:
        router_result["intent"] = "shop_info_question"
        router_result["product_query"] = None
        router_result["confidence"] = max(router_result.get("confidence", 0.0), 0.95)
    elif is_catalog_request:
        router_result["intent"] = "product_list"
        router_result["product_query"] = None
        router_result["confidence"] = max(router_result.get("confidence", 0.0), 0.95)
    elif indexed_product:
        router_result["intent"] = "product_info_question"
        router_result["confidence"] = max(router_result.get("confidence", 0.0), 0.95)
    elif _contains_word(msg_norm, greeting_terms):
        router_result["intent"] = "greeting"
        router_result["product_query"] = None
        router_result["confidence"] = max(router_result.get("confidence", 0.0), 0.95)
    elif _contains_word(msg_norm, small_talk_terms):
        router_result["intent"] = "small_talk"
        router_result["product_query"] = None
        router_result["confidence"] = max(router_result.get("confidence", 0.0), 0.9)
    elif state.get("pending_order_json") and _is_pending_order_field_reply(
        msg_norm,
        bool(state.get("delivery_city")),
    ):
        router_result["intent"] = "order_creation"
        router_result["confidence"] = max(router_result.get("confidence", 0.0), 0.95)
    elif _is_order_creation_signal(message, msg_norm):
        router_result["intent"] = "order_creation"
        router_result["confidence"] = max(router_result.get("confidence", 0.0), 0.95)
    elif _contains_any(msg_norm, delivery_terms) and not is_cash_on_delivery:
        router_result["intent"] = "delivery_question"
        router_result["confidence"] = max(router_result.get("confidence", 0.0), 0.95)
    elif _contains_any(msg_norm, payment_terms):
        router_result["intent"] = "payment_question"
        router_result["confidence"] = max(router_result.get("confidence", 0.0), 0.95)
    elif _contains_any(msg_norm, price_terms):
        router_result["intent"] = "price_question"
        router_result["confidence"] = max(router_result.get("confidence", 0.0), 0.95)
    elif _contains_any(msg_norm, availability_terms):
        router_result["intent"] = "availability_question"
        router_result["confidence"] = max(router_result.get("confidence", 0.0), 0.95)
    elif _contains_any(msg_norm, order_terms):
        router_result["intent"] = "order_creation"
        router_result["confidence"] = max(router_result.get("confidence", 0.0), 0.95)
    elif explicit_product and _contains_any(msg_norm, info_terms):
        router_result["intent"] = "product_info_question"
        router_result["confidence"] = max(router_result.get("confidence", 0.0), 0.9)

    if not router_result.get("product_query") and active_product and not is_shop_info_request and not is_catalog_request:
        uses_context = _contains_any(
            msg_lower,
            [" it", "this", "that product", "same one", "this one", "how much", "price", "available", "stock", "deliver", "brand", "had", "hada", "hadi"],
        )
        uses_context = uses_context or _contains_any(msg_norm, ["livraison", "katsifto", "tsifto", "sifto"])
        if uses_context:
            router_result["product_query"] = active_product

    if city:
        state["steps"].append(f"Detected delivery city: {city}")
    if address:
        state["steps"].append(f"Detected delivery address: {address}")

    return router_result


def build_router_prompt(
    message: str,
    known_products: list[str],
    active_product: Optional[str] = None,
    last_catalog_products: Optional[list[str]] = None,
    pending_order_json: Optional[dict] = None,
) -> tuple[str, str]:
    """
    Build system and user prompts for LLM-based router.
    
    Args:
        message: Current user message
        known_products: List of available product names
        active_product: Currently active product in session
        last_catalog_products: Products from the last catalog response
        pending_order_json: Current pending order context
        
    Returns:
        tuple: (system_prompt, user_prompt)
    """
    system_prompt = ROUTER_SYSTEM_PROMPT
    
    user_prompt = ROUTER_USER_PROMPT_TEMPLATE.format(
        message=message,
        known_products=json.dumps(known_products, indent=2),
        active_product=active_product if active_product else "None",
        last_catalog_products=json.dumps(last_catalog_products or [], indent=2),
        pending_order_json=json.dumps(pending_order_json or {}, indent=2),
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
            state.get("active_product"),
            state.get("last_catalog_products"),
            state.get("pending_order_json"),
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
    msg_norm = _normalize_text(state["message"])
    is_shop_info_request = _is_shop_info_request(msg_norm)
    is_catalog_request = _is_catalog_request(msg_norm) or _is_catalog_comparison_request(msg_norm)
    catalog_filter = _catalog_filter_field(msg_norm, state["shop_data"])
    if catalog_filter and not find_product(state["message"], state["shop_data"]):
        is_catalog_request = True
    
    # Initialize result
    result = {
        "intent": "unknown",
        "product_query": None,
        "confidence": 0.85,  # Deterministic is less confident than LLM
        "needs_human": False
    }
    
    # Try to find a product in the message
    product = find_product(state["message"], state["shop_data"])
    indexed_product = _product_from_catalog_index(msg_norm, state)
    if product:
        result["product_query"] = product["name"]
    elif indexed_product:
        result["product_query"] = indexed_product
    
    if is_shop_info_request:
        result["intent"] = "shop_info_question"
        result["product_query"] = None
        result["confidence"] = 0.95
    
    elif is_catalog_request:
        result["intent"] = "product_list"
        result["product_query"] = None
        result["confidence"] = 0.95
    
    elif indexed_product:
        result["intent"] = "product_info_question"
        result["confidence"] = 0.95
    
    # Order creation field replies should not be routed as delivery questions.
    elif _is_order_creation_signal(state["message"], msg_norm):
        result["intent"] = "order_creation"
        if product:
            result["product_query"] = product["name"]
        elif state.get("active_product"):
            result["product_query"] = state["active_product"]
        result["confidence"] = 0.95

    # Delivery has priority because "how much" can mean delivery cost/time.
    elif _contains_any(msg_norm, ["delivery", "deliver", "shipping", "ship", "address", "city", "cities", "delivery cost", "delivery price", "how much time", "how long", "arrive", "livraison", "katsifto", "tsifto", "sifto"]) and "cash on delivery" not in msg_norm:
        result["intent"] = "delivery_question"
        result["confidence"] = 0.95
    
    # Payment patterns
    elif _contains_any(msg_norm, ["payment", "pay", "cash on delivery", "cash", "card", "transfer", "bank transfer", "paypal", "paiement", "payer", "virement"]):
        result["intent"] = "payment_question"
        result["product_query"] = None
        result["confidence"] = 0.95
    
    # Price patterns
    elif _contains_any(msg_norm, ["price", "cost", "how much", "expensive", "cheap", "cheapest", "discount", "promo", "prix", "combien", "ch7al", "chhal", "taman", "tamane"]):
        result["intent"] = "price_question"
        if product:
            result["product_query"] = product["name"]
        elif state.get("active_product"):
            result["product_query"] = state["active_product"]
        result["confidence"] = 0.95
    
    # Availability patterns
    elif _contains_any(msg_norm, ["available", "availability", "in stock", "stock", "disponible", "kayn", "kayna", "mawjod", "mawjoude"]):
        result["intent"] = "availability_question"
        if product:
            result["product_query"] = product["name"]
        elif state.get("active_product"):
            result["product_query"] = state["active_product"]
        result["confidence"] = 0.95
    
    # Order intent
    elif _contains_any(msg_norm, ["i want to order", "i want to buy", "place order", "confirm order", "checkout", "buy", "order", "purchase", "reserve", "confirm", "i want it", "take it", "send it to me", "can i buy", "bghit", "ncommandi", "commander", "commande", "acheter"]):
        result["intent"] = "order_creation"
        if product:
            result["product_query"] = product["name"]
        elif state.get("active_product"):
            result["product_query"] = state["active_product"]
        result["confidence"] = 0.95
    
    # Greeting patterns (use word boundary to avoid matching "hi" in "this")
    elif _contains_word(msg_norm, ["hello", "hi", "salam", "slm", "hey", "bonjour", "slt", "salut"]):
        result["intent"] = "greeting"
        result["confidence"] = 0.95
    
    # Small talk patterns
    elif _contains_word(msg_norm, ["thank you", "thanks", "ok", "okay", "bye", "good", "understood", "merci", "chokran", "shokran", "la", "non"]):
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
