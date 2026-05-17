"""Focused router and memory tests for the commerce assistant."""

from lg_app.data.shop_data import SHOP_PRODUCTS
from lg_app.memory import session_store
from lg_app.nodes.router import deterministic_intent_router, intent_router
from lg_app.runner import run_chat
from lg_app.state import ChatState


def make_state(message: str, active_product: str | None = None) -> ChatState:
    return {
        "session_id": "router-test",
        "shop_id": "demo",
        "message": message,
        "intent": None,
        "product_query": None,
        "active_product": active_product,
        "current_product": active_product,
        "current_product_name": active_product,
        "delivery_city": None,
        "response": None,
        "steps": [],
        "shop_data": SHOP_PRODUCTS,
        "needs_human": False,
        "confidence": 0.0,
    }


def assert_route(message: str, expected_intent: str, expected_product: str | None = None) -> ChatState:
    state = intent_router(make_state(message))
    assert state["intent"] == expected_intent, (message, state["intent"], state["steps"])
    assert state["product_query"] == expected_product, (message, state["product_query"], state["steps"])
    return state


print("\nRouter priority tests")

assert_route("What is the price of Hair Oil?", "price_question", "Hair Oil")
assert_route("How much is Hair Oil?", "price_question", "Hair Oil")
assert_route("How much does Hair Oil cost?", "price_question", "Hair Oil")

delivery_state = assert_route("How much is delivery to Casablanca?", "delivery_question", None)
assert delivery_state["delivery_city"] == "Casablanca"

assert_route("How much time for delivery?", "delivery_question", None)
assert_route("Tell me more about Hair Oil", "product_info_question", "Hair Oil")
assert_route("Can I pay cash on delivery?", "payment_question", None)

print("Router priority tests passed")


print("\nDeterministic fallback tests")

deterministic_cases = [
    ("Is Hair Oil available?", "availability_question", "Hair Oil"),
    ("How much is Hair Oil?", "price_question", "Hair Oil"),
    ("How much is delivery to Casablanca?", "delivery_question", None),
    ("Can I pay cash on delivery?", "payment_question", None),
]

for message, expected_intent, expected_product in deterministic_cases:
    result = deterministic_intent_router(make_state(message))
    assert result["intent"] == expected_intent, (message, result)
    assert result["product_query"] == expected_product, (message, result)

print("Deterministic fallback tests passed")


print("\nConversation memory tests")

session_id = "conversation-a"
session_store.sessions.pop(session_id, None)

first = run_chat(session_id, "Is Hair Oil available?")
assert first["intent"] == "availability_question", first
assert first["current_product"] == "Hair Oil", first

second = run_chat(session_id, "How much is it?")
assert second["intent"] == "price_question", second
assert second["current_product"] == "Hair Oil", second

third = run_chat(session_id, "How much is delivery to Casablanca?")
assert third["intent"] == "delivery_question", third
assert third["current_product"] == "Hair Oil", third
assert third["delivery_city"] == "Casablanca", third

fourth = run_chat(session_id, "How can I pay?")
assert fourth["intent"] == "payment_question", fourth
assert fourth["current_product"] == "Hair Oil", fourth

session_id = "conversation-b"
session_store.sessions.pop(session_id, None)
result = run_chat(session_id, "How much is Hair Oil?")
assert result["intent"] == "price_question", result
assert result["current_product"] == "Hair Oil", result

session_id = "conversation-c"
session_store.sessions.pop(session_id, None)
result = run_chat(session_id, "Tell me more about Hair Oil")
assert result["intent"] == "product_info_question", result
assert result["current_product"] == "Hair Oil", result

session_id = "conversation-d"
session_store.sessions.pop(session_id, None)
result = run_chat(session_id, "Can I pay cash on delivery?")
assert result["intent"] == "payment_question", result

print("Conversation memory tests passed")
print("\nAll quick tests passed")
