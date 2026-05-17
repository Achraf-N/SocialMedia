"""Node: Price agent."""

import json
from app.state import ChatState
from app.llm import get_llm
from app.llm.prompts import SYSTEM_PROMPTS, PROMPT_TEMPLATES


def price_agent(state: ChatState) -> ChatState:
    """Handle price inquiry using Ollama LLM."""
    
    if not state["active_product"]:
        state["response"] = "Could you tell me which product you mean?"
        state["steps"].append("Generated price response")
        return state
    
    # Find the active product
    product = None
    for p in state["shop_data"]:
        if p["name"] == state["active_product"]:
            product = p
            break
    
    if not product:
        state["response"] = "Could you tell me which product you mean?"
        state["steps"].append("Generated price response")
        return state
    
    # Generate response using Ollama LLM
    try:
        llm = get_llm()
        
        shop_data_json = json.dumps([{
            "name": p["name"],
            "price": p["price"],
            "available": p["available"],
        } for p in state["shop_data"]], indent=2)
        
        prompt = PROMPT_TEMPLATES["price"].format(
            message=state["message"],
            shop_data=shop_data_json,
            active_product=state["active_product"]
        )
        
        response_text = llm.generate(
            prompt=prompt,
            system=SYSTEM_PROMPTS["price"],
            temperature=0.3,
            max_tokens=128,
        )
        
        # Parse JSON response
        result = json.loads(response_text)
        state["response"] = result.get("response", f"{product['name']} is {product['price']} MAD.")
    
    except (json.JSONDecodeError, Exception):
        # Fallback to deterministic response if LLM fails or JSON parsing fails
        if product["available"]:
            state["response"] = f"{product['name']} is {product['price']} MAD."
        else:
            state["response"] = f"{product['name']} is {product['price']} MAD, but currently unavailable."
    
    state["steps"].append("Generated price response")
    return state
