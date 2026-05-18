"""Focused router and memory tests for the commerce assistant."""

from lg_app.data.shop_data import SHOP_PRODUCTS
from lg_app.memory import session_store
from lg_app.nodes.router import deterministic_intent_router, intent_router
from lg_app.nodes.order import order_agent
from lg_app.runner import run_chat
from lg_app.state import ChatState

TEST_SHOP_ID = "test-shop"
SPORTS_PRODUCTS = [
    {
        "name": "Nike Air Max 270",
        "price": 1299,
        "description": "Comfortable Nike lifestyle sneakers.",
        "available": True,
        "category": "Sneakers",
        "stock": 15,
        "delivery_time": "24-72h",
        "brand": "Nike",
        "variants": ["EU 42"],
        "image": "",
    },
    {
        "name": "Nike Dri-FIT Training T-Shirt",
        "price": 349,
        "description": "Lightweight Nike training shirt.",
        "available": True,
        "category": "Sportswear",
        "stock": 30,
        "delivery_time": "24-72h",
        "brand": "Nike",
        "variants": ["M"],
        "image": "",
    },
    {
        "name": "Adidas Ultraboost Light",
        "price": 1499,
        "description": "Responsive Adidas running shoes.",
        "available": True,
        "category": "Sneakers",
        "stock": 10,
        "delivery_time": "24-72h",
        "brand": "Adidas",
        "variants": ["EU 42"],
        "image": "",
    },
]


def make_state(message: str, active_product: str | None = None) -> ChatState:
    return {
        "session_id": "router-test",
        "shop_id": "demo",
        "message": message,
        "intent": None,
        "product_query": None,
        "active_product": active_product,
        "current_product_id": None,
        "current_product": active_product,
        "current_product_name": active_product,
        "delivery_city": None,
        "delivery_address": None,
        "pending_order_json": None,
        "shop_info": None,
        "catalog_filter": None,
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
assert_route("what is the shop name", "shop_info_question", None)
assert_route("what is service provided by this store", "product_list", None)
assert_route("what are products details in this shop", "product_list", None)
expensive_state = assert_route("give me the expensive one", "product_list", None)
assert expensive_state["delivery_city"] is None
other_prices_state = assert_route("give me the price for all other products", "product_list", None)
assert other_prices_state["delivery_city"] is None

print("Router priority tests passed")


print("\nBrand/catalog routing tests")

brand_state = make_state("give me more details about Nike")
brand_state["shop_data"] = SPORTS_PRODUCTS
brand_result = intent_router(brand_state)
assert brand_result["intent"] == "product_list", brand_result
assert brand_result["product_query"] is None, brand_result
assert brand_result["catalog_filter"] == "Nike", brand_result

print("Brand/catalog routing tests passed")


print("\nOrder field extraction tests")

order_state = make_state("Achraf 0612345678 12 Rue X, Casablanca", "Hair Oil")
order_state["pending_order_json"] = {"product_id": "hair-oil-id", "quantity": 1}
order_state["shop_data"] = [
    {
        **SHOP_PRODUCTS[1],
        "id": "hair-oil-id",
    }
]
order_state = intent_router(order_state)
assert order_state["intent"] == "order_intent", order_state
order_state["delivery_city"] = None
order_state = order_agent(order_state)
assert order_state["pending_order_json"]["customer_name"] == "Achraf", order_state
assert order_state["pending_order_json"]["customer_phone"] == "0612345678", order_state
assert "12 Rue X" in order_state["pending_order_json"]["address"], order_state

pending_switch = make_state("how much is Hair Oil?", "Hair Oil")
pending_switch["pending_order_json"] = {"product_id": "hair-oil-id", "quantity": 1}
pending_switch = intent_router(pending_switch)
assert pending_switch["intent"] == "price_question", pending_switch

print("Order field extraction tests passed")


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

first = run_chat(session_id, "Is Hair Oil available?", TEST_SHOP_ID)
assert first["intent"] == "availability_question", first
assert first["current_product"] == "Hair Oil", first

second = run_chat(session_id, "How much is it?", TEST_SHOP_ID)
assert second["intent"] == "price_question", second
assert second["current_product"] == "Hair Oil", second

third = run_chat(session_id, "How much is delivery to Casablanca?", TEST_SHOP_ID)
assert third["intent"] == "delivery_question", third
assert third["current_product"] == "Hair Oil", third
assert third["delivery_city"] == "Casablanca", third

fourth = run_chat(session_id, "How can I pay?", TEST_SHOP_ID)
assert fourth["intent"] == "payment_question", fourth
assert fourth["current_product"] == "Hair Oil", fourth

session_id = "conversation-catalog-switch"
session_store.sessions.pop(session_id, None)
selected = run_chat(session_id, "give me the expensive one", TEST_SHOP_ID)
assert selected["intent"] == "product_list", selected
assert selected["current_product"] == "Serum Vitamin C", selected
follow_up = run_chat(session_id, "how much is it?", TEST_SHOP_ID)
assert follow_up["intent"] == "price_question", follow_up
assert follow_up["current_product"] == "Serum Vitamin C", follow_up

session_id = "conversation-b"
session_store.sessions.pop(session_id, None)
result = run_chat(session_id, "How much is Hair Oil?", TEST_SHOP_ID)
assert result["intent"] == "price_question", result
assert result["current_product"] == "Hair Oil", result

session_id = "conversation-c"
session_store.sessions.pop(session_id, None)
result = run_chat(session_id, "Tell me more about Hair Oil", TEST_SHOP_ID)
assert result["intent"] == "product_info_question", result
assert result["current_product"] == "Hair Oil", result

session_id = "conversation-d"
session_store.sessions.pop(session_id, None)
result = run_chat(session_id, "Can I pay cash on delivery?", TEST_SHOP_ID)
assert result["intent"] == "payment_question", result

print("Conversation memory tests passed")
print("\nAll quick tests passed")
