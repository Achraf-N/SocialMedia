# Quick Start Visual Guide

## Step 1: Setup (Terminal 1)
```bash
# Install and start Ollama
ollama pull qwen3:8b
ollama serve

# Output:
# 2024/05/17 10:00:00 Listening on 127.0.0.1:11434
```

## Step 2: Run Tests (Terminal 2)
```bash
cd langgraph
pip install -r requirements.txt

# Test connection
python example_config.py test-connection
# Output: ✓ Ollama working: Ollama is working!

# Run full conversation
python -m app.runner
# Shows 8-message test conversation with LLM responses
```

## Step 3: Integration Flow

### Input
```
User Message: "Tell me about Serum Vitamin C"
Session: "user_123"
```

### LangGraph Processing
```
1. load_shop_data
   → Loads 3 beauty products into state

2. load_session_state
   → Retrieves previous context (active_product, last_intent)

3. intent_router
   → Detects intent: "product_info_question"
   → Finds product: "Serum Vitamin C"

4. update_active_product
   → Sets active_product = "Serum Vitamin C"

5. [Routing Decision]
   → Route to product_info_agent (matched intent)

6. product_info_agent (LLM-POWERED)
   ┌─────────────────────────────────────┐
   │ Build Prompt                        │
   │ System: "You are a helpful..."      │
   │ User: "Product: Serum Vitamin C..." │
   └─────────────────────────────────────┘
           │
           ↓
   ┌─────────────────────────────────────┐
   │ Call Ollama API                     │
   │ POST http://localhost:11434/api/gen │
   │ model: qwen3:8b                     │
   │ temperature: 0.7                    │
   │ max_tokens: 256                     │
   └─────────────────────────────────────┘
           │
           ↓
   ┌─────────────────────────────────────┐
   │ LLM Response (qwen3:8b)             │
   │ "Serum Vitamin C is available. It   │
   │  is a brightening serum for dark    │
   │  spots and is highly rated."        │
   └─────────────────────────────────────┘

7. save_session_state
   → Saves: active_product = "Serum Vitamin C"
   → Saves: last_intent = "product_info_question"
```

### Output
```json
{
  "response": "Serum Vitamin C is available. It is a brightening serum for dark spots and is highly rated.",
  "intent": "product_info_question",
  "active_product": "Serum Vitamin C",
  "steps": [
    "Received message",
    "Loaded shop data",
    "Loaded session state",
    "Detected intent: product_info_question",
    "Updated active product: Serum Vitamin C",
    "Generated product info response",
    "Saved session state"
  ]
}
```

## File Structure Quick Reference

```
langgraph/
│
├── app/
│   ├── llm/                    ← Ollama integration
│   │   ├── __init__.py         ← OllamaLLM class
│   │   └── prompts.py          ← Prompt templates
│   │
│   ├── nodes/                  ← Agent nodes
│   │   ├── product_list.py     (LLM)
│   │   ├── product_info.py     (LLM) ← Example
│   │   ├── price.py            (LLM)
│   │   ├── delivery.py         (LLM)
│   │   ├── payment.py          (LLM)
│   │   ├── greeting.py         (LLM)
│   │   ├── small_talk.py       (LLM)
│   │   ├── unknown.py          (LLM)
│   │   └── human_needed.py     (LLM)
│   │
│   ├── state.py                ← ChatState TypedDict
│   ├── graph.py                ← Workflow graph
│   ├── runner.py               ← run_chat() function
│   ├── data/
│   ├── memory/
│   └── utils/
│
├── example_config.py           ← Testing examples
├── OLLAMA_INTEGRATION.md       ← Detailed guide
├── INTEGRATION_SUMMARY.md      ← Setup summary
├── README.md                   ← Main documentation
└── requirements.txt
```

## Common Commands

```bash
# Test LLM connection
python example_config.py test-connection

# Test specific agent
python example_config.py test-product

# Test all agents
python example_config.py test-all

# Full workflow test
python -m app.runner

# Use in Python code
from app.runner import run_chat
result = run_chat("user1", "Hello")
```

## Customization Quick Tips

### 🎭 Change Agent Tone
File: `app/llm/prompts.py`
```python
SYSTEM_PROMPTS["product_info"] = """Your custom role here"""
```

### 🎚️ Adjust Response Style
File: Agent node (e.g., `product_info.py`)
```python
response = llm.generate(
    prompt=prompt,
    system=SYSTEM_PROMPTS["product_info"],
    temperature=0.9,      # More creative
    max_tokens=512,       # Longer response
)
```

### 🤖 Use Different Model
File: `app/llm/__init__.py`
```python
def get_llm(model: str = "mistral") -> OllamaLLM:
```

### ⚡ Test & Debug
```python
# In Python
from app.runner import run_chat

# Test a message
result = run_chat("test_user", "your message")
print(result["response"])
print(result["steps"])
```

## Troubleshooting Matrix

| Issue | Solution |
|-------|----------|
| "Connection refused" | Make sure `ollama serve` is running |
| Model not found | Run `ollama pull qwen3:8b` |
| Slow responses | Try smaller model: `ollama pull mistral` |
| Bad responses | Adjust prompts in `app/llm/prompts.py` |
| Import errors | Check `pip install -r requirements.txt` |

## API Contract (for Backend)

Your backend can call:

```python
from app.runner import run_chat

def chat_endpoint(session_id: str, message: str) -> dict:
    return run_chat(session_id, message)

# Returns
{
    "response": str,           # Bot's LLM response
    "intent": str,            # Detected intent
    "active_product": str,    # Product in context
    "steps": list[str]        # Workflow steps
}
```

---

**Everything is LLM-powered with Ollama qwen3:8b. Ready to use! 🚀**
