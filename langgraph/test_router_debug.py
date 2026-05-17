"""Debug router detection."""

from app.nodes.router import deterministic_intent_router
from app.state import ChatState
from app.data.shop_data import SHOP_PRODUCTS

test_messages = [
    "What is the price of this product?",
    "Tell me about Serum Vitamin C",
    "How much?",
    "What about Hair Oil?",
]

for msg in test_messages:
    state: ChatState = {
        'session_id': 'test',
        'message': msg,
        'intent': None,
        'product_query': None,
        'active_product': 'Serum Vitamin C',
        'response': None,
        'steps': [],
        'shop_data': SHOP_PRODUCTS,
        'needs_human': False,
        'confidence': 0.0,
    }
    
    result = deterministic_intent_router(state)
    print(f"Message: '{msg}'")
    print(f"  Intent: {result['intent']}")
    print(f"  Product: {result['product_query']}")
    print(f"  Confidence: {result['confidence']}")
    print()
