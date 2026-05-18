"""Node: Unknown intent agent."""

from lg_app.state import ChatState
from lg_app.llm import get_llm
from lg_app.llm.prompts import SYSTEM_PROMPTS, PROMPT_TEMPLATES


def unknown_agent(state: ChatState) -> ChatState:
    """Handle unknown intent using Ollama LLM."""
    if state.get("active_product"):
        state["response"] = (
            f"Do you want the price, availability, delivery, payment, or order help for {state['active_product']}?"
        )
        state["steps"].append("Generated contextual unknown response")
        return state
    
    # Generate response using Ollama LLM
    try:
        llm = get_llm()
        
        prompt = PROMPT_TEMPLATES["unknown"].format(
            message=state["message"],
        )
        
        response = llm.generate(
            prompt=prompt,
            system=SYSTEM_PROMPTS["unknown"],
            temperature=0.3,
            max_tokens=128,
        )
    
    except Exception as e:
        # Fallback to deterministic response if LLM fails
        response = "Sure. Are you asking about products, price, delivery, payment, or placing an order?"
    
    state["response"] = response
    state["steps"].append("Generated unknown response")
    
    return state
