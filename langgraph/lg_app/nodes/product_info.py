"""Node: Product info agent."""

import json
import re
from lg_app.state import ChatState
from lg_app.llm import get_llm
from lg_app.llm.prompts import SYSTEM_PROMPTS, PROMPT_TEMPLATES
from lg_app.data.shop_data import SHOP_INFO


def product_info_agent(state: ChatState) -> ChatState:
    """Handle product information request using Ollama LLM."""
    
    if not state["active_product"]:
        state["response"] = "Could you tell me which product you mean?"
        state["steps"].append("Generated product info response")
        return state
    
    # Find the active product
    product = None
    for p in state["shop_data"]:
        if p["name"] == state["active_product"]:
            product = p
            break
    
    if not product:
        state["response"] = "Could you tell me which product you mean?"
        state["steps"].append("Generated product info response")
        return state

    message = state["message"].lower()
    if re.search(r"\b(product\s*\d+|\d+(?:st|nd|rd|th)\s+one|first one|second one|third one|fourth one|the first|the second|the third|the fourth)\b", message):
        details = (product.get("description") or "No description available yet.").rstrip(" .")
        price = product.get("price")
        stock = product.get("stock")
        brand = product.get("brand")
        parts = [f"{product['name']}: {details}"]
        if price is not None:
            parts.append(f"Price: {price} MAD")
        if brand:
            parts.append(f"Brand: {brand}")
        if stock is not None:
            parts.append(f"Stock: {stock}")
        state["response"] = ". ".join(parts) + "."
        state["steps"].append("Generated product info response")
        return state

    if "brand" in message:
        brand = product.get("brand")
        if brand:
            state["response"] = f"{product['name']} is from {brand}."
        else:
            state["response"] = f"The brand for {product['name']} is not available yet."
        state["steps"].append("Generated product brand response")
        return state
    
    # Generate response using Ollama LLM
    try:
        llm = get_llm()
        
        shop_data_json = json.dumps([{
            "name": p["name"],
            "description": p["description"],
            "price": p["price"],
            "available": p["available"],
            "brand": p["brand"],
            "stock": p["stock"],
        } for p in state["shop_data"]], indent=2)
        
        prompt = PROMPT_TEMPLATES["product_info"].format(
            message=state["message"],
            shop_data=shop_data_json,
            active_product=state["active_product"]
        )
        
        response_text = llm.generate(
            prompt=prompt,
            system=SYSTEM_PROMPTS["product_info"],
            temperature=0.3,
            max_tokens=256,
        )
        
        # Parse JSON response
        result = json.loads(response_text)
        state["response"] = result.get("response", "Product information not available.")
    
    except (json.JSONDecodeError, Exception):
        # Fallback to deterministic response if LLM fails or JSON parsing fails
        if product["available"]:
            state["response"] = f"{product['name']} is available. {product['description']}"
        else:
            state["response"] = f"{product['name']} is currently unavailable. {product['description']}"
    
    state["steps"].append("Generated product info response")
    return state
