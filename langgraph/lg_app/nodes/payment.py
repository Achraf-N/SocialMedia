"""Node: Payment agent."""

from lg_app.state import ChatState
from lg_app.data.shop_data import SHOP_INFO
from lg_app.llm import get_llm
from lg_app.llm.prompts import SYSTEM_PROMPTS, PROMPT_TEMPLATES


def payment_agent(state: ChatState) -> ChatState:
    """Handle payment inquiry using Ollama LLM."""
    
    # Generate response using Ollama LLM
    try:
        llm = get_llm()
        
        shop_info = state.get("shop_info") or SHOP_INFO
        payment_info = shop_info.get("payment") or SHOP_INFO.get("payment")

        prompt = PROMPT_TEMPLATES["payment"].format(
            message=state["message"],
            payment_info=payment_info or "Payment information is not available yet.",
        )
        
        response = llm.generate(
            prompt=prompt,
            system=SYSTEM_PROMPTS["payment"],
            temperature=0.3,
            max_tokens=256,
        )
    
    except Exception as e:
        # Fallback to deterministic response if LLM fails
        response = (state.get("shop_info") or SHOP_INFO).get("payment") or "Payment information is not available yet."
    
    state["response"] = response
    state["steps"].append("Generated payment response")
    
    return state
