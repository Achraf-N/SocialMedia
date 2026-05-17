"""Node: Greeting agent."""

from lg_app.state import ChatState
from lg_app.llm import get_llm
from lg_app.llm.prompts import SYSTEM_PROMPTS, PROMPT_TEMPLATES


def greeting_agent(state: ChatState) -> ChatState:
    """Handle greeting using Ollama LLM."""
    
    # Generate response using Ollama LLM
    try:
        llm = get_llm()
        
        prompt = PROMPT_TEMPLATES["greeting"].format(
            message=state["message"],
        )
        
        response = llm.generate(
            prompt=prompt,
            system=SYSTEM_PROMPTS["greeting"],
            temperature=0.8,
            max_tokens=128,
        )
    
    except Exception as e:
        # Fallback to deterministic response if LLM fails
        response = "Hello! How can I help you today?"
    
    state["response"] = response
    state["steps"].append("Generated greeting response")
    
    return state
