"""Node: Unknown intent agent."""

from app.state import ChatState
from app.llm import get_llm
from app.llm.prompts import SYSTEM_PROMPTS, PROMPT_TEMPLATES


def unknown_agent(state: ChatState) -> ChatState:
    """Handle unknown intent using Ollama LLM."""
    
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
        response = "I didn't fully understand your request. Could you tell me which product or information you need?"
    
    state["response"] = response
    state["steps"].append("Generated unknown response")
    
    return state
