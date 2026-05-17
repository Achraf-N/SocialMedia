"""Node: Small talk agent."""

from lg_app.state import ChatState
from lg_app.llm import get_llm
from lg_app.llm.prompts import SYSTEM_PROMPTS, PROMPT_TEMPLATES


def small_talk_agent(state: ChatState) -> ChatState:
    """Handle small talk using Ollama LLM."""
    
    # Generate response using Ollama LLM
    try:
        llm = get_llm()
        
        prompt = PROMPT_TEMPLATES["small_talk"].format(
            message=state["message"],
        )
        
        response = llm.generate(
            prompt=prompt,
            system=SYSTEM_PROMPTS["small_talk"],
            temperature=0.8,
            max_tokens=128,
        )
    
    except Exception as e:
        # Fallback to deterministic response if LLM fails
        response = "You're welcome! 😊 Let me know if you need anything else."
    
    state["response"] = response
    state["steps"].append("Generated small talk response")
    
    return state
