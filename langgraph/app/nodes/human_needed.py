"""Node: Human escalation agent."""

from app.state import ChatState
from app.llm import get_llm
from app.llm.prompts import SYSTEM_PROMPTS, PROMPT_TEMPLATES


def human_needed_agent(state: ChatState) -> ChatState:
    """Handle complaints or requests requiring human support using Ollama LLM."""
    
    # Generate response using Ollama LLM
    try:
        llm = get_llm()
        
        prompt = PROMPT_TEMPLATES["complaint"].format(
            message=state["message"],
        )
        
        response = llm.generate(
            prompt=prompt,
            system=SYSTEM_PROMPTS["complaint"],
            temperature=0.3,
            max_tokens=256,
        )
    
    except Exception as e:
        # Fallback to deterministic response if LLM fails
        response = "I'm sorry about the issue. I'll forward your request to the shop owner for assistance."
    
    state["response"] = response
    state["steps"].append("Generated human escalation response")
    
    return state
