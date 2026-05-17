# LangGraph Conversational AI Workflow

A pure LangGraph workflow module for a social media/website sales assistant chatbot with **Ollama LLM integration**. This is **only the workflow layer** — no FastAPI, database, or frontend included.

## What This Is

This is a **LangGraph state machine** that handles conversational AI logic for a beauty product sales assistant. It:

- Detects user intent from messages
- Routes to specialized agent nodes
- **Uses Ollama (qwen3:8b) for natural language generation**
- Maintains session context (active product, conversation history)
- Manages product queries and responses
- Tracks workflow progress

## Architecture

### Workflow Flow

```
START
  ↓
load_shop_data (load products into state)
  ↓
load_session_state (retrieve previous context)
  ↓
intent_router (detect user intent & product)
  ↓
update_active_product (set current product context)
  ↓
route_by_intent (conditional routing)
  ↓
[Agent Node based on Intent]:
  - product_list_agent
  - product_info_agent
  - price_agent
  - delivery_agent
  - payment_agent
  - greeting_agent
  - small_talk_agent
  - human_needed_agent
  - unknown_agent
  ↓
save_session_state (persist context)
  ↓
END
```

### State Structure (TypedDict)

```python
ChatState = {
    "session_id": str,              # User session ID
    "message": str,                 # Input message
    "intent": str | None,           # Detected intent
    "product_query": str | None,    # Product mentioned
    "active_product": str | None,   # Current product context
    "response": str | None,         # Bot response
    "steps": list[str],             # Progress tracking
    "shop_data": list[dict],        # Product database
    "needs_human": bool             # Escalation flag
}
```

## Project Structure

```
langgraph/
├── app/
│   ├── __init__.py
│   ├── state.py                 # ChatState TypedDict
│   ├── graph.py                 # StateGraph & routing
│   ├── runner.py                # run_chat() function & tests
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   └── shop_data.py         # Products & shop info
│   │
│   ├── llm/
│   │   ├── __init__.py          # Ollama LLM interface
│   │   └── prompts.py           # System & template prompts
│   │
│   ├── memory/
│   │   ├── __init__.py
│   │   └── session_store.py     # In-memory session storage
│   │
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── load_shop_data.py
│   │   ├── load_session_state.py
│   │   ├── router.py
│   │   ├── state_manager.py
│   │   ├── product_list.py      # LLM-powered
│   │   ├── product_info.py      # LLM-powered
│   │   ├── price.py             # LLM-powered
│   │   ├── delivery.py          # LLM-powered
│   │   ├── payment.py           # LLM-powered
│   │   ├── greeting.py          # LLM-powered
│   │   ├── small_talk.py        # LLM-powered
│   │   ├── unknown.py           # LLM-powered
│   │   ├── human_needed.py      # LLM-powered
│   │   └── save_session_state.py
│   │
│   └── utils/
│       ├── __init__.py
│       └── product_matcher.py   # Product detection
│
├── example_config.py            # Configuration & testing examples
├── requirements.txt
└── README.md (this file)
```

## Installation

### 1. Install Python Dependencies

```bash
cd langgraph
pip install -r requirements.txt
```

### 2. Install & Run Ollama

Download and install Ollama: https://ollama.ai

Then pull the qwen3:8b model:

```bash
ollama pull qwen3:8b
```

Start the Ollama server:

```bash
ollama serve
```

This runs on `http://localhost:11434` (default).

## Usage

### Run Test Conversation

```bash
python -m app.runner
```

This runs an 8-message test conversation showing:
1. Greeting
2. Product list request
3. Product info query
4. Price inquiry
5. Different product query
6. Price for current product
7. Delivery inquiry
8. Small talk

### Use in Your Code

```python
from app.runner import run_chat

# Run a single chat message
result = run_chat("user_123", "What products do you have?")

print(result["response"])          # Bot's response
print(result["intent"])            # Detected intent
print(result["active_product"])    # Current product (if any)
print(result["steps"])             # Workflow steps
```

### Return Format

```python
{
    "response": "We currently offer Serum Vitamin C, Hair Oil.",
    "intent": "product_list",
    "active_product": None,
    "steps": [
        "Received message",
        "Loaded shop data",
        "Loaded session state",
        "Detected intent: product_list",
        "Updated active product: None",
        "Generated product list response",
        "Saved session state"
    ]
}
```

## Intents Supported

| Intent | Keywords | Agent |
|--------|----------|-------|
| **greeting** | hello, hi, salam, hey | greeting_agent |
| **small_talk** | thank you, thanks, ok, bye, good | small_talk_agent |
| **product_list** | products, catalog, what do you offer, what do you sell | product_list_agent |
| **product_info_question** | details, explain, info, available, usage, ingredients | product_info_agent |
| **price_question** | price, cost, how much | price_agent |
| **delivery_question** | delivery, shipping, arrive, cities | delivery_agent |
| **payment_question** | payment, pay, cash, card, bank transfer | payment_agent |
| **complaint** | refund, problem, angry, late, bad | human_needed_agent |
| **human_needed** | support, order not arrived | human_needed_agent |
| **unknown** | (none matched) | unknown_agent |

## Session Memory

In-memory session storage tracks per-session context:

```python
sessions = {
    "user_123": {
        "active_product": "Serum Vitamin C",
        "last_intent": "price_question"
    }
}
```

**Functions:**

```python
from app.memory.session_store import get_session_state, save_session_state

# Get session
session = get_session_state("user_123")

# Save session
save_session_state("user_123", active_product="Hair Oil", last_intent="price_question")
```

## Product Matching

The `find_product()` function matches product mentions in messages:

```python
from app.utils.product_matcher import find_product

products = [...]  # from SHOP_PRODUCTS
result = find_product("Tell me about vitamin c", products)
# returns: {"nameLLM-Powered)

Each uses **Ollama qwen3:8b** with prompt engineering:

- **product_list_agent**: Generates natural product introduction
- **product_info_agent**: Generates product description with availability
- **price_agent**: Provides price in conversational tone
- **delivery_agent**: Explains delivery terms naturally
- **payment_agent**: Explains payment options reassuringly
- **greeting_agent**: Generates warm greeting
- **small_talk_agent**: Responds to casual conversation
- **unknown_agent**: Asks clarifying questions
- **human_needed_agent**: Handles complaints with empathy

All include fallback logic for when LLM is unavailable.ate
- **load_session_state**: Retrieves user's previous session context

### Processing Nodes

- **intent_router**: Detects intent and product query using regex patterns
- **update_active_product**: Updates or maintains active product in session

### Agent Nodes (Deterministic - No LLM yet)

Each generates a simple response based on state:

- **product_list_agent**: Lists available/unavailable products
- **product_info_agent**: Shows product details or asks for clarification
- **price_agent**: Quotes product price or asks for product specification
- **delivery_agent**: Returns delivery terms from shop info
- **payment_agent**: Returns payment options from shop info
- **greeting_agent**: Returns greeting
- **small_talk_agent**: Returns acknowledgment
- **unknown_agent**: Returns clarification request
- **human_needed_agent**: Returns escalation message

### Final Node

- **save_sCustom Prompts

Edit prompts in `app/llm/prompts.py`:

```python
# System prompts (role/context)
SYSTEM_PROMPTS = {
    "product_info": "Your custom system prompt here...",
    # ... other agents
}

# Prompt templates (facts to use)
PROMPT_TEMPLATES = {
    "product_info": """Your template here with {placeholder} variables""",
    # ... other agents
}
```

For example, to make product_info more detailed:

```python
SYSTEM_PROMPTS["product_info"] = """You are an expert beauty consultant.
Provide detailed, personalized product recommendations.
Consider user needs and skin type."""

PROMPT_TEMPLATES["product_info"] = """Product: {name}
{description}
Price: {price} MAD
Brand: {brand}
Stock: {stock}

Explain this product's benefits in detail."""
```

## Configuration

### Ollama Settings

In `app/llm/__init__.py`, customize:

```python
def get_llm(model: str = "qwen3:8b") -> OllamaLLM:
    # Change model name
    # Change base_url for remote Ollama server
    # ...
```

### LLM Parameters per Agent

In each agent node:
- **temperature**: 0.7 (balanced), 0.8 (creative) - customize in `llm.generate()` calls
- **max_tokens**: 128-256 - adjust based on expected response length)
state["response"] = response.content
```

## Testing

### Unit Testing

```bash
python -m pytest  # (add tests as needed)
```

### Manual Testing

```bash
python -m app.runner
```

Outputs an 8-message test conversation with full workflow steps.

## Integration with Backend

Your FastAPI backend can import and use this:

```python
from fastapi import FastAPI
from app.runner import run_chat

app = FastAPI()

@app.post("/chat")
async def chat(request: ChatRequest):
    result = run_chat(request.session_id, request.message)
    return ChatResponse(**result)
```

The backend (`/backend` folder) can call `run_chat()` to get bot responses.

## Features

✅ **LangGraph StateGraph** - 13 nodes with conditional routing
✅ **9 Intent Types** - Comprehensive intent detection
✅ **Ollama qwen3:8b** - Local LLM, no API costs
✅ **Prompt Engineering** - Customizable system & template prompts
✅ **Session Memory** - Tracks context per user
✅ **Product Matching** - Fuzzy product name detection
✅ **Fallback Logic** - Works without LLM when needed
✅ **Progress Tracking** - Steps for frontend UI
✅ **Clean Modular Code** - Easy to extend
✅ **Runnable Tests** - Included test conversation

## Dependencies

- `langgraph==0.0.26` - Workflow orchestration
- `langchain==0.1.1` - Utilities
- `typing-extensions==4.9.0` - TypedDict support
- `requests==2.31.0` - Ollama API calls

## Troubleshooting

### "Could not connect to Ollama at http://localhost:11434"

Make sure Ollama is running:
```bash
ollama serve
```

### Model not found error

Pull the model:
```bash
ollama pull qwen3:8b
```

Or change the model in `app/llm/__init__.py`:
```python
def get_llm(model: str = "llama2") -> OllamaLLM:  # Use llama2 instead
```

### Responses are slow

- Qwen3:8b should be fast on most systems
- Try a smaller model: `ollama pull phi` (2.7B) or `ollama pull mistral` (7B)
- Increase timeout in `app/llm/__init__.py` if needed

### LLM responses not good quality

Adjust prompts in `app/llm/prompts.py`:
- Make system prompts more detailed
- Add examples to templates
- Adjust temperature: lower (0.3-0.5) for consistency, higher (0.8-1.0) for variety

## Notes

- **This is ONLY the workflow layer** — no FastAPI, database, or frontend
- **Ollama integration**: All agent nodes use qwen3:8b
- **Session storage**: In-memory (use database for persistence)
- **Fallback**: Each node has deterministic fallback if LLM unavailable
- **Ready for integration**: Backend API or direct Python imports

## Next Steps

1. **Fine-tune Prompts** - Customize `app/llm/prompts.py` for your domain
2. **Database** - Replace in-memory sessions with persistent storage
3. **Performance** - Use smaller model or quantized version if needed
4. **Analytics** - Track intents, conversations, user behavior
5. **Multi-language** - Add language support to prompts

---

**LangGraph workflow with Ollama LLM — Ready to integrate with your backend!**
