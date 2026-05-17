# Verification Guide - Router LLM Implementation

## Quick Verification

### Step 1: Check Files Exist

```bash
# From langgraph/ directory

# Check new prompt file
ls app/prompts/router_prompt.py
# ✅ Should exist

# Check updated files
ls app/nodes/router.py
ls app/state.py
ls app/runner.py
# ✅ All should exist
```

### Step 2: Verify Imports Work

```python
# In Python
from app.prompts.router_prompt import ROUTER_SYSTEM_PROMPT, ROUTER_USER_PROMPT_TEMPLATE
from app.nodes.router import build_router_prompt, route_with_llm, deterministic_intent_router, intent_router
from app.state import ChatState

print("✅ All imports successful")
```

### Step 3: Test Router Functions

```python
# Test build_router_prompt()
from app.nodes.router import build_router_prompt

system, user = build_router_prompt(
    "Tell me about serum",
    ["Serum Vitamin C", "Hair Oil", "Face Cream"],
    "Hair Oil"
)

print("System Prompt (first 100 chars):", system[:100])
print("User Prompt:", user)
print("✅ build_router_prompt() works")
```

### Step 4: Test Deterministic Router

```python
from app.nodes.router import deterministic_intent_router
from app.state import ChatState

state: ChatState = {
    "session_id": "test",
    "message": "Show me products",
    "intent": None,
    "product_query": None,
    "active_product": None,
    "response": None,
    "steps": [],
    "shop_data": [
        {"name": "Serum Vitamin C"},
        {"name": "Hair Oil"},
    ],
    "needs_human": False,
    "confidence": 0.0,
}

result = deterministic_intent_router(state)
print("Router Result:", result)
print("✅ deterministic_intent_router() works")

# Expected:
# {
#     "intent": "product_list",
#     "product_query": None,
#     "confidence": 0.95,
#     "needs_human": False
# }
```

### Step 5: Test Full Workflow

```python
from app.runner import run_chat

result = run_chat("user1", "Hello")
print("Result:", result)

# Should include:
# - response: str
# - intent: str
# - product_query: str or None
# - active_product: str or None
# - confidence: float  ← NEW
# - steps: list[str]

print("✅ Full workflow works")
```

## Detailed Verification Checklist

### Code Structure
- [ ] `app/prompts/__init__.py` exists (empty module file)
- [ ] `app/prompts/router_prompt.py` exists (contains prompts)
- [ ] `ROUTER_SYSTEM_PROMPT` defined in router_prompt.py
- [ ] `ROUTER_USER_PROMPT_TEMPLATE` defined in router_prompt.py

### Router Node Updates
- [ ] `app/nodes/router.py` has imports: `json`, `Optional`, `ROUTER_SYSTEM_PROMPT`, `ROUTER_USER_PROMPT_TEMPLATE`
- [ ] `build_router_prompt()` function exists
- [ ] `route_with_llm()` function exists with TODO
- [ ] `deterministic_intent_router()` function exists
- [ ] `intent_router()` orchestrates both modes
- [ ] Supports all 10 intents

### State Updates
- [ ] `app/state.py` has `confidence: float` field
- [ ] `ChatState` TypedDict includes confidence

### Runner Updates
- [ ] `app/runner.py` initializes `confidence` in initial_state
- [ ] Returns `confidence` in response dict

### Intent Types
- [ ] greeting ✅
- [ ] small_talk ✅
- [ ] product_list ✅
- [ ] product_info_question ✅
- [ ] price_question ✅
- [ ] delivery_question ✅ **NEW**
- [ ] payment_question ✅ **NEW**
- [ ] complaint ✅
- [ ] human_needed ✅
- [ ] unknown ✅

### Routing Keywords
**Delivery:**
- [ ] "delivery"
- [ ] "shipping"
- [ ] "arrive"
- [ ] "cities"
- [ ] "how long"

**Payment:**
- [ ] "payment"
- [ ] "pay"
- [ ] "cash"
- [ ] "card"
- [ ] "bank transfer"

### Output Format
```python
{
    "response": "...",
    "intent": "...",
    "product_query": "..." or None,
    "active_product": "..." or None,
    "confidence": 0.95,  # ← NEW
    "steps": [...]
}
```

## Test Cases

### Test 1: Simple Intent
```python
result = run_chat("u1", "hello")
assert result["intent"] == "greeting"
assert result["confidence"] == 0.95
print("✅ Test 1: Greeting")
```

### Test 2: Product List
```python
result = run_chat("u1", "what do you offer?")
assert result["intent"] == "product_list"
assert result["confidence"] == 0.95
print("✅ Test 2: Product List")
```

### Test 3: Delivery Question
```python
result = run_chat("u1", "how long is delivery?")
assert result["intent"] == "delivery_question"
assert result["confidence"] == 0.95
print("✅ Test 3: Delivery Question")
```

### Test 4: Payment Question
```python
result = run_chat("u1", "can i pay with card?")
assert result["intent"] == "payment_question"
assert result["confidence"] == 0.95
print("✅ Test 4: Payment Question")
```

### Test 5: Confidence in Steps
```python
result = run_chat("u1", "products")
assert any("confidence:" in step for step in result["steps"])
print("✅ Test 5: Confidence in Steps")
```

## Run Full Tests

```bash
cd langgraph
python -m app.runner

# Should output:
# ================================================================================
# LangGraph Chatbot - Test Conversation
# ================================================================================
#
# [User] hello
# [Bot] Hello! How can I help you today?
# [Intent] greeting
# [Active Product] None
# [Steps]
#   - Received message
#   - Loaded shop data
#   - Loaded session state
#   - Detected intent: greeting (confidence: 0.95)  ← Shows confidence
#   ...
```

## Debug Output

Enable debugging with:
```python
import json
from app.nodes.router import build_router_prompt

# Print prompts
system, user = build_router_prompt(
    "test message",
    ["Product A", "Product B"],
    None
)

print("=== SYSTEM PROMPT ===")
print(system)
print("\n=== USER PROMPT ===")
print(user)
```

## LLM Router Verification

When LLM router is implemented, verify:

```python
# Check TODO is implemented
def route_with_llm(state: ChatState, use_llm: bool = False) -> dict:
    if use_llm:
        # Should call: llm.generate(prompt, system, temperature, max_tokens)
        # Should return: dict with intent, product_query, confidence, needs_human
        pass
    return None

# Enable LLM
router_result = route_with_llm(state, use_llm=True)
assert router_result is not None, "LLM router not implemented"
```

## Performance Check

```python
import time
from app.runner import run_chat

start = time.time()
result = run_chat("u1", "test message")
elapsed = time.time() - start

print(f"Deterministic router: {elapsed*1000:.2f}ms")
# Should be < 10ms

print(f"Confidence: {result['confidence']}")
# Should be 0.85-0.95
```

## Integration Check

Verify no breaking changes:
- [ ] `app/graph.py` still works
- [ ] All agent nodes still work
- [ ] Session memory still works
- [ ] LLM agents still work
- [ ] No import errors
- [ ] No syntax errors

## Documentation Check

- [ ] `ROUTER_UPDATE.md` exists
- [ ] `ROUTER_IMPLEMENTATION.md` exists
- [ ] `QUICK_START.md` updated (if needed)
- [ ] Code has docstrings
- [ ] Functions documented
- [ ] TODO comments present

## Final Verification

```bash
# Run all tests
python -m pytest  # If tests exist

# Run full workflow
python -m app.runner

# Check no errors
# Look for "Detected intent: X (confidence: Y)" in output
# Verify confidence shows 0.85-0.95
```

## Expected Output Pattern

Every router detection should show:
```
Detected intent: {intent_name} (confidence: {0.85-0.95})
```

Examples:
```
Detected intent: greeting (confidence: 0.95)
Detected intent: product_list (confidence: 0.95)
Detected intent: delivery_question (confidence: 0.95)
Detected intent: small_talk (confidence: 0.9)
Detected intent: unknown (confidence: 0.85)
```

---

✅ **If all checks pass, router LLM implementation is successful!**
