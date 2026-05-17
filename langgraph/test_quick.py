"""Quick test: Router + Session State Management (no LLM delays)."""

from app.nodes.router import deterministic_intent_router
from app.memory.session_store import get_session_state, save_session_state
from app.state import ChatState
from app.data.shop_data import SHOP_PRODUCTS

print("\n" + "="*80)
print("Router + Session State - Quick Test")
print("="*80 + "\n")

# TEST 1: Session isolation
print("[TEST 1] Session isolation")
save_session_state("user_a", active_product="Serum Vitamin C", last_intent="product_info")
save_session_state("user_b", active_product="Hair Oil", last_intent="price_question")

session_a = get_session_state("user_a")
session_b = get_session_state("user_b")

assert session_a["active_product"] == "Serum Vitamin C", "User A should have Serum"
assert session_b["active_product"] == "Hair Oil", "User B should have Hair Oil"
print(f"  User A: {session_a}")
print(f"  User B: {session_b}")
print("✓ PASS - Sessions are isolated\n")

# TEST 2: Router with active_product context
print("[TEST 2] Router context awareness")

state_with_context: ChatState = {
    'session_id': 'test',
    'message': 'What is the price of this product?',
    'intent': None,
    'product_query': None,
    'active_product': 'Serum Vitamin C',
    'response': None,
    'steps': [],
    'shop_data': SHOP_PRODUCTS,
    'needs_human': False,
    'confidence': 0.0,
}

result = deterministic_intent_router(state_with_context)
print(f"  Message: 'What is the price of this product?'")
print(f"  Active product: 'Serum Vitamin C'")
print(f"  Router detected: intent={result['intent']}, product_query={result['product_query']}")
assert result['intent'] == 'price_question', "Should detect price_question"
print("✓ PASS - Router correctly detects price_question\n")

# TEST 3: Router without context
print("[TEST 3] Router without context (explicit product mention)")

state_explicit: ChatState = {
    'session_id': 'test',
    'message': 'What about Hair Oil?',
    'intent': None,
    'product_query': None,
    'active_product': None,
    'response': None,
    'steps': [],
    'shop_data': SHOP_PRODUCTS,
    'needs_human': False,
    'confidence': 0.0,
}

result = deterministic_intent_router(state_explicit)
print(f"  Message: 'What about Hair Oil?'")
print(f"  Active product: None")
print(f"  Router detected: intent={result['intent']}, product_query={result['product_query']}")
assert result['intent'] == 'product_info_question', "Should detect product_info_question"
assert result['product_query'] == 'Hair Oil', "Should extract Hair Oil product"
print("✓ PASS - Router correctly extracts product mention\n")

# TEST 4: Word boundary fix
print("[TEST 4] Word boundary detection (hi in 'this')")

problematic_messages = [
    "What is the price of this product?",  # Should NOT match 'hi' in 'this'
    "Hi there!",  # Should match 'hi'
    "This is great",  # Should NOT match 'hi' in 'this'
]

expected_intents = [
    "price_question",
    "greeting",
    "unknown",
]

for msg, expected in zip(problematic_messages, expected_intents):
    state: ChatState = {
        'session_id': 'test',
        'message': msg,
        'intent': None,
        'product_query': None,
        'active_product': None,
        'response': None,
        'steps': [],
        'shop_data': SHOP_PRODUCTS,
        'needs_human': False,
        'confidence': 0.0,
    }
    
    result = deterministic_intent_router(state)
    print(f"  '{msg}' → {result['intent']}")
    assert result['intent'] == expected, f"Expected {expected}, got {result['intent']}"

print("✓ PASS - Word boundary detection works correctly\n")

# TEST 5: Confidence scores
print("[TEST 5] Confidence scores")

test_cases = [
    ("hello", "greeting", 0.95),
    ("thanks", "small_talk", 0.9),
    ("products", "product_list", 0.95),
    ("tell me details", "product_info_question", 0.9),
    ("how much", "price_question", 0.95),
    ("delivery time", "delivery_question", 0.95),
    ("can I pay", "payment_question", 0.95),
    ("angry", "complaint", 0.95),
]

for msg, expected_intent, expected_confidence in test_cases:
    state: ChatState = {
        'session_id': 'test',
        'message': msg,
        'intent': None,
        'product_query': None,
        'active_product': None,
        'response': None,
        'steps': [],
        'shop_data': SHOP_PRODUCTS,
        'needs_human': False,
        'confidence': 0.0,
    }
    
    result = deterministic_intent_router(state)
    print(f"  '{msg}' → {result['intent']} (confidence: {result['confidence']})")
    assert result['intent'] == expected_intent
    assert result['confidence'] == expected_confidence

print("✓ PASS - Confidence scores correct\n")

print("="*80)
print("ALL QUICK TESTS PASSED! ✓")
print("="*80)
print("\nSummary:")
print("✓ Session isolation works")
print("✓ Router context awareness works")
print("✓ Product extraction works")
print("✓ Word boundary detection fixed")
print("✓ Confidence scores assigned correctly")
print("✓ active_product session state persists correctly")
