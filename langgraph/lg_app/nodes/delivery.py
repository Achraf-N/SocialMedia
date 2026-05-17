"""Node: Delivery agent."""

from lg_app.state import ChatState
from lg_app.data.shop_data import SHOP_INFO
from lg_app.llm import get_llm
from lg_app.llm.prompts import SYSTEM_PROMPTS, PROMPT_TEMPLATES


def delivery_agent(state: ChatState) -> ChatState:
    """Handle delivery inquiry using Ollama LLM."""
    
    # Generate response using Ollama LLM
    try:
        llm = get_llm()
        
        prompt = PROMPT_TEMPLATES["delivery"].format(
            message=state["message"],
            delivery_info=SHOP_INFO["delivery"],
        )
        
        response = llm.generate(
            prompt=prompt,
            system=SYSTEM_PROMPTS["delivery"],
            temperature=0.3,
            max_tokens=256,
        )
    
    except Exception as e:
        # Fallback to deterministic response if LLM fails
        response = SHOP_INFO["delivery"]
    
    state["response"] = response
    state["steps"].append("Generated delivery response")
    
    return state
