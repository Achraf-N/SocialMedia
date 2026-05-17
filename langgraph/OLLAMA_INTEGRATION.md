"""
OLLAMA INTEGRATION GUIDE
========================

This document explains how the LangGraph workflow integrates with Ollama qwen3:8b.
"""

# ============================================================================
# 1. ARCHITECTURE OVERVIEW
# ============================================================================

"""
LangGraph Workflow with Ollama:

┌─────────────────────────────────────────────────────────────────┐
│                        LangGraph Nodes                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  load_shop_data → load_session_state → intent_router           │
│                        ↓                                        │
│                  update_active_product                         │
│                        ↓                                        │
│              [LLM-Powered Agent Nodes]                         │
│              ┌─────────────────────┐                           │
│              │ • product_list_agent │ ←→ Ollama API           │
│              │ • product_info_agent │    (qwen3:8b)           │
│              │ • price_agent       │    http://localhost:11434│
│              │ • delivery_agent    │    /api/generate         │
│              │ • payment_agent     │                          │
│              │ • greeting_agent    │                          │
│              │ • small_talk_agent  │                          │
│              │ • unknown_agent     │                          │
│              │ • human_needed_agent│                          │
│              └─────────────────────┘                           │
│                        ↓                                        │
│              save_session_state                                │
│                        ↓                                        │
│                      END                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
"""

# ============================================================================
# 2. HOW LLM INTEGRATION WORKS
# ============================================================================

"""
Each agent node follows this pattern:

def agent_node(state: ChatState) -> ChatState:
    try:
        # 1. Get LLM instance
        llm = get_llm()
        
        # 2. Build prompt from template with context data
        prompt = PROMPT_TEMPLATES["agent_name"].format(
            product_name=...,
            description=...,
            # ... other variables
        )
        
        # 3. Generate response using LLM
        response = llm.generate(
            prompt=prompt,
            system=SYSTEM_PROMPTS["agent_name"],  # Role/context
            temperature=0.7,                        # Creativity level
            max_tokens=256,                         # Length limit
        )
        
    except Exception as e:
        # 4. Fallback to deterministic response if LLM fails
        response = "Fallback response..."
    
    state["response"] = response
    state["steps"].append("Generated response")
    return state


Example: product_info_agent

Input state:
{
    "active_product": "Serum Vitamin C",
    "shop_data": [{...}, {...}],
    ...
}

Template:
"Product: {name}\nDescription: {description}\nAvailable: {available}\n..."

System Prompt:
"You are a helpful beauty product sales assistant..."

Ollama Request:
POST http://localhost:11434/api/generate
{
    "model": "qwen3:8b",
    "prompt": "[system prompt]\n\n[template with values]",
    "temperature": 0.7,
    "num_predict": 256,
    "stream": false
}

LLM Response:
"Serum Vitamin C is available. It is a brightening serum for dark spots."

Output state:
{
    "response": "Serum Vitamin C is available. It is a brightening serum for dark spots.",
    "active_product": "Serum Vitamin C",
    ...
}
"""

# ============================================================================
# 3. PROMPT ENGINEERING BREAKDOWN
# ============================================================================

"""
Each LLM call uses TWO parts:

1. SYSTEM PROMPT (Role & Context)
   └─ Defines the AI's persona and rules
   └─ Example:
      "You are a helpful beauty product sales assistant.
       Keep responses concise (1-2 sentences) and natural."

2. USER PROMPT (Task & Facts)
   └─ Contains specific task and data
   └─ Uses template variables
   └─ Example:
      "Product: Serum Vitamin C
       Description: Brightening serum for dark spots
       Available: Yes
       Price: 149 MAD
       
       Generate a natural, friendly response about this product."

Combined in LLM:
┌──────────────────────────────────┐
│ System Prompt                    │
├──────────────────────────────────┤
│ [Blank line]                     │
├──────────────────────────────────┤
│ User Prompt (task + facts)       │
└──────────────────────────────────┘
"""

# ============================================================================
# 4. CUSTOMIZING PROMPTS
# ============================================================================

"""
File: app/llm/prompts.py

To improve LLM responses:

a) SYSTEM PROMPTS - Make role more specific:

Before:
"You are a helpful beauty product sales assistant."

After:
"You are a luxury beauty consultant with 10 years experience.
 You specialize in skincare and anti-aging products.
 Your goal is to provide personalized recommendations.
 Always mention ingredients and benefits.
 Use sophisticated, professional language."

b) PROMPT TEMPLATES - Add more context:

Before:
"Product: {name}
 Description: {description}
 Generate a response about this product."

After:
"Customer Interest: {customer_interest}
 Product: {name}
 Brand: {brand}
 Description: {description}
 Price: {price} MAD
 Stock: {stock}
 Best for: {best_for}
 
 Recommend this product to the customer.
 Explain why it suits their needs.
 Mention the price naturally."

c) TEMPERATURE - Adjust creativity:

- 0.1-0.3: Deterministic (consistent, factual)
- 0.5-0.7: Balanced (natural, slightly creative)
- 0.8-1.0: Creative (varied, storytelling)

Current settings:
product_info_agent: temperature=0.7 (balanced)
greeting_agent: temperature=0.8 (creative)
price_agent: temperature=0.7 (balanced)
"""

# ============================================================================
# 5. FALLBACK MECHANISM
# ============================================================================

"""
If Ollama is down or erroring, LangGraph uses fallback:

Agent Node with Fallback:

try:
    llm = get_llm()
    response = llm.generate(prompt, system, temperature, max_tokens)
except Exception as e:
    # FALLBACK: Simple deterministic response
    response = "Simple response without LLM"

This ensures the chatbot continues working even if:
- Ollama server is down
- Model is not loaded
- Network connection lost
- Timeout occurs
"""

# ============================================================================
# 6. PERFORMANCE PARAMETERS
# ============================================================================

"""
Parameters in app/llm/__init__.py:

class OllamaLLM:
    def __init__(
        self,
        model: str = "qwen3:8b",        # Model name
        base_url: str = "http://localhost:11434"  # Ollama server
    )
    
    def generate(
        self,
        prompt: str,                    # Main task
        temperature: float = 0.7,       # 0-1: creativity
        max_tokens: int = 256,          # Response length
        system: Optional[str] = None,   # System prompt
        timeout: int = 60               # Request timeout
    )

Tuning for speed vs quality:

FAST (< 1 second):
- model: phi (2.7B) or mistral (7B)
- temperature: 0.5
- max_tokens: 128

BALANCED (1-3 seconds):
- model: qwen3:8b (default)
- temperature: 0.7
- max_tokens: 256

QUALITY (3-10 seconds):
- model: qwen3:14b (larger)
- temperature: 0.6
- max_tokens: 512
"""

# ============================================================================
# 7. TESTING LLM INTEGRATION
# ============================================================================

"""
Testing provided in example_config.py:

python example_config.py test-connection
└─ Checks if Ollama is running

python example_config.py test-product
└─ Tests product_info_agent with LLM

python example_config.py test-all
└─ Full conversation with all agents

python -m app.runner
└─ Full 8-message test conversation
"""

# ============================================================================
# 8. MODIFYING AN AGENT NODE
# ============================================================================

"""
Example: Improve product_info_agent

File: app/nodes/product_info.py

Current:
    prompt = PROMPT_TEMPLATES["product_info"].format(
        product_name=product["name"],
        name=product["name"],
        description=product["description"],
        available="Yes" if product["available"] else "No",
        price=product["price"],
        brand=product["brand"],
        stock=product["stock"],
        delivery_time=product["delivery_time"],
    )
    
    response = llm.generate(
        prompt=prompt,
        system=SYSTEM_PROMPTS["product_info"],
        temperature=0.7,
        max_tokens=256,
    )

Modified for luxury products:
    prompt = PROMPT_TEMPLATES["product_info"].format(
        product_name=product["name"],
        name=product["name"],
        description=product["description"],
        available="Yes" if product["available"] else "No",
        price=product["price"],
        brand=product["brand"],
        stock=product["stock"],
        delivery_time=product["delivery_time"],
        rating=product.get("rating", "4.5/5"),
        reviews=product.get("reviews", "1200+"),
    )
    
    response = llm.generate(
        prompt=prompt,
        system=SYSTEM_PROMPTS["product_info"],  # Change to luxury system prompt
        temperature=0.6,  # More consistent
        max_tokens=512,   # Longer responses
    )

And update the template in app/llm/prompts.py:
    "product_info": """Product: {name} by {brand}
    Rating: {rating} ({reviews} reviews)
    Price: {price} MAD
    Availability: {available}
    
    Description: {description}
    Delivery: {delivery_time}
    
    Provide a detailed, luxury product recommendation
    that addresses quality, benefits, and value."""
"""

# ============================================================================
# 9. ADDING NEW AGENTS
# ============================================================================

"""
To add a new agent (e.g., review_agent):

1. Create app/nodes/review.py:
   
   def review_agent(state: ChatState) -> ChatState:
       try:
           llm = get_llm()
           prompt = PROMPT_TEMPLATES["review"].format(
               product_name=state["active_product"],
               # ... other variables
           )
           response = llm.generate(
               prompt=prompt,
               system=SYSTEM_PROMPTS["review"],
               temperature=0.8,
               max_tokens=256,
           )
       except Exception:
           response = "Could you tell me which product's reviews you want?"
       
       state["response"] = response
       state["steps"].append("Generated review response")
       return state

2. Add prompts in app/llm/prompts.py:
   
   SYSTEM_PROMPTS["review"] = "You are a helpful product review assistant..."
   PROMPT_TEMPLATES["review"] = "Product: {product_name}...\nShow reviews."

3. Add node to app/graph.py:
   
   from app.nodes.review import review_agent
   
   graph.add_node("review_agent", review_agent)
   graph.add_edge("review_agent", "save_session_state")

4. Add intent to app/nodes/router.py:
   
   elif any(word in msg_lower for word in ["review", "feedback", "rating"]):
       intent = "review_question"

5. Add conditional route in app/graph.py:
   
   "review_question": "review_agent",
"""

# ============================================================================
# 10. PRODUCTION CONSIDERATIONS
# ============================================================================

"""
Before deploying:

1. Performance
   - Use quantized models (Q4, Q5 formats)
   - Run Ollama on GPU server for speed
   - Implement response caching

2. Reliability
   - Add circuit breaker for LLM failures
   - Monitor Ollama server uptime
   - Use smaller model as fallback

3. Customization
   - Fine-tune prompts for your domain
   - Test with real user conversations
   - Adjust temperature per intent type

4. Monitoring
   - Log all LLM requests/responses
   - Track response quality metrics
   - Monitor latency and failures

5. Scaling
   - Use multiple Ollama instances
   - Implement load balancing
   - Cache frequently asked questions
"""

print(__doc__)
