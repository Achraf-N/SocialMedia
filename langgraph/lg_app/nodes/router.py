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
            temperature=0.3,
            max_tokens=256
        )
        
        # Parse JSON from LLM
        result = json.loads(response_text)
        return result
    
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
    
    # Greeting patterns (use word boundary to avoid matching "hi" in "this")
    if _contains_word(msg_lower, ["hello", "hi", "salam", "hey"]):
        result["intent"] = "greeting"
        result["confidence"] = 0.95
    
    # Small talk patterns
    elif _contains_word(msg_lower, ["thank you", "thanks", "ok", "okay", "bye", "good", "understood"]):
        result["intent"] = "small_talk"
        result["confidence"] = 0.9
    
    # Product list patterns
    elif _contains_word(msg_lower, ["products", "catalog", "what do you offer", "what services", "what do you sell", "available products", "what do you provide", "what can i buy"]):
        result["intent"] = "product_list"
        result["product_query"] = None
        result["confidence"] = 0.95
    
    # Product info patterns (or product mentioned)
    elif _contains_word(msg_lower, ["details", "explain", "info", "available", "usage", "benefits", "ingredients"]) or product:
        result["intent"] = "product_info_question"
        if product:
            result["product_query"] = product["name"]
        result["confidence"] = 0.9
    
    # Price patterns
    elif _contains_word(msg_lower, ["price", "cost", "discount"]) or "how much" in msg_lower:
        result["intent"] = "price_question"
        result["confidence"] = 0.95
    
    # Delivery patterns
    elif _contains_word(msg_lower, ["delivery", "shipping", "cities"]) or "how long" in msg_lower or "arrive" in msg_lower:
        result["intent"] = "delivery_question"
        result["product_query"] = None
        result["confidence"] = 0.95
    
    # Payment patterns
    elif _contains_word(msg_lower, ["payment", "pay", "cash", "card"]) or "bank transfer" in msg_lower:
        result["intent"] = "payment_question"
        result["product_query"] = None
        result["confidence"] = 0.95
    
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
    # Try LLM router first (currently returns None, enabling fallback)
    router_result = route_with_llm(state, use_llm=False)
    
    # Fall back to deterministic if LLM not available
    if router_result is None:
        router_result = deterministic_intent_router(state)
    
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
