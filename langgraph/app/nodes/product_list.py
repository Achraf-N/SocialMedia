"""Node: Product list agent."""

import json
from app.state import ChatState
from app.llm import get_llm
from app.llm.prompts import SYSTEM_PROMPTS, PROMPT_TEMPLATES


def product_list_agent(state: ChatState) -> ChatState:
    """Handle product list request using Ollama LLM."""
    
    # Generate response using Ollama LLM
    try:
        llm = get_llm()
        
        shop_data_json = json.dumps([{
            "name": p["name"],
            "price": p["price"],
            "description": p["description"],
            "available": p["available"],
        } for p in state["shop_data"]], indent=2)
        
        prompt = PROMPT_TEMPLATES["product_list"].format(
            message=state["message"],
            shop_data=shop_data_json,
        )
        
        response_text = llm.generate(
            prompt=prompt,
            system=SYSTEM_PROMPTS["product_list"],
            temperature=0.3,
            max_tokens=256,
        )
        
        # Parse JSON response
        result = json.loads(response_text)
        state["response"] = result.get("response", "We offer various products. Please ask for more details.")
    
    except (json.JSONDecodeError, Exception):
        # Fallback to deterministic response if LLM fails
        available_products = [p["name"] for p in state["shop_data"] if p["available"]]
        
        if available_products:
            state["response"] = f"We currently offer: {', '.join(available_products)}. Would you like to know more about any of them?"
        else:
            state["response"] = "Sorry, all products are currently unavailable. Please check back later."
    
    state["steps"].append("Generated product list response")
    return state
