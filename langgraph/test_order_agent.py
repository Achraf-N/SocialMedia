"""Order creation tests for the LangGraph agent."""

from lg_app.nodes.order import order_agent
from lg_app.nodes.router import deterministic_intent_router
from lg_app.nodes.state_manager import update_active_product
from lg_app.state import ChatState


PRODUCTS = [
    {
        "id": "prod-123",
        "name": "Hair Oil",
        "price": 99,
        "description": "Natural oil for dry hair",
        "available": True,
        "stock": 12,
    }
    ,
    {
        "id": "prod-456",
        "name": "Face Cream",
        "price": 120,
        "description": "Hydrating face cream",
        "available": True,
        "stock": 7,
    },
]


def make_state(message: str, active_product_id: str | None = "prod-123") -> ChatState:
    active_product = "Hair Oil" if active_product_id else None
    return {
        "session_id": "test-session",
        "shop_id": "shop-123",
        "message": message,
        "intent": None,
        "product_query": None,
        "active_product": active_product,
        "active_product_id": active_product_id,
        "active_product_name": active_product,
        "current_product_id": active_product_id,
        "current_product": active_product,
        "current_product_name": active_product,
        "delivery_city": None,
        "delivery_address": None,
        "pending_order_json": None,
        "shop_info": None,
        "catalog_filter": None,
        "last_catalog_products": None,
        "response": None,
        "steps": [],
        "shop_data": PRODUCTS,
        "needs_human": False,
        "confidence": 0.0,
    }


def test_selected_product_stored_with_id():
    state = make_state("tell me about Hair Oil", active_product_id=None)
    state["product_query"] = "Hair Oil"

    result = update_active_product(state)

    assert result["active_product_id"] == "prod-123"
    assert result["active_product_name"] == "Hair Oil"


def test_order_agent_calls_backend_with_product_id_quantity_and_customer_info(monkeypatch):
    calls = []

    def fake_create_order(payload):
        calls.append(payload)
        return {"message": "Order created successfully"}

    monkeypatch.setattr("lg_app.backend_client.create_order", fake_create_order)
    state = make_state(
        "name: tom, phone: 0661612345, city: rabat, delivery address: rabat ville, quantity: 2"
    )

    result = order_agent(state)

    assert calls == [
        {
            "shop_id": "shop-123",
            "session_id": "test-session",
            "product_id": "prod-123",
            "quantity": 2,
            "customer_info": {
                "name": "tom",
                "phone": "0661612345",
                "city": "rabat",
                "delivery_address": "rabat ville",
            },
        }
    ]
    assert result["response"] == "Order created successfully"
    assert result["pending_order_json"] is None


def test_order_agent_defaults_quantity_to_one(monkeypatch):
    calls = []

    def fake_create_order(payload):
        calls.append(payload)
        return {"message": "Order created successfully"}

    monkeypatch.setattr("lg_app.backend_client.create_order", fake_create_order)
    state = make_state("name: tom, phone: 0661612345, city: rabat, delivery address: rabat ville")

    order_agent(state)

    assert calls[0]["quantity"] == 1


def test_order_agent_extracts_quantity_words(monkeypatch):
    calls = []

    def fake_create_order(payload):
        calls.append(payload)
        return {"message": "Order created successfully"}

    monkeypatch.setattr("lg_app.backend_client.create_order", fake_create_order)
    state = make_state("I need two stuff, name: tom, phone: 0661612345, city: rabat, delivery address: rabat ville")

    order_agent(state)

    assert calls[0]["quantity"] == 2


def test_order_agent_extracts_quantity_before_product_name(monkeypatch):
    calls = []

    def fake_create_order(payload):
        calls.append(payload)
        return {"message": "Order created successfully"}

    monkeypatch.setattr("lg_app.backend_client.create_order", fake_create_order)
    state = make_state(
        "I need to order three Hair Oil, name: tom, phone: 0661612345, city: rabat, delivery address: rabat ville"
    )

    order_agent(state)

    assert calls[0]["quantity"] == 3


def test_order_agent_calls_backend_with_multiple_items(monkeypatch):
    calls = []

    def fake_create_order(payload):
        calls.append(payload)
        return {"message": "Order created successfully", "total_price": 219}

    monkeypatch.setattr("lg_app.backend_client.create_order", fake_create_order)
    state = make_state(
        "I want to order Hair Oil and Face Cream, name: tom, phone: 0661612345, city: rabat, delivery address: rabat ville"
    )

    result = order_agent(state)

    assert calls[0]["items"] == [
        {"product_id": "prod-123", "quantity": 1},
        {"product_id": "prod-456", "quantity": 1},
    ]
    assert "product_id" not in calls[0]
    assert "Total: 219 MAD" in result["response"]


def test_order_agent_uses_last_catalog_for_these_three_products(monkeypatch):
    calls = []

    def fake_create_order(payload):
        calls.append(payload)
        return {"message": "Order created successfully", "total_price": 339}

    monkeypatch.setattr("lg_app.backend_client.create_order", fake_create_order)
    state = make_state(
        "I want to order these 2 products, name: tom, phone: 0661612345, city: rabat, delivery address: rabat ville"
    )
    state["last_catalog_products"] = ["Hair Oil", "Face Cream"]

    order_agent(state)

    assert calls[0]["items"] == [
        {"product_id": "prod-123", "quantity": 1},
        {"product_id": "prod-456", "quantity": 1},
    ]


def test_order_agent_uses_last_catalog_for_two_different_products(monkeypatch):
    calls = []

    def fake_create_order(payload):
        calls.append(payload)
        return {"message": "Order created successfully", "total_price": 219}

    monkeypatch.setattr("lg_app.backend_client.create_order", fake_create_order)
    state = make_state(
        "I want to order two different products, name: tom, phone: 0661612345, city: rabat, delivery address: rabat ville"
    )
    state["last_catalog_products"] = ["Hair Oil", "Face Cream"]

    order_agent(state)

    assert calls[0]["items"] == [
        {"product_id": "prod-123", "quantity": 1},
        {"product_id": "prod-456", "quantity": 1},
    ]


def test_order_agent_asks_when_different_products_are_not_identified(monkeypatch):
    calls = []

    def fake_create_order(payload):
        calls.append(payload)
        return {"message": "Order created successfully"}

    monkeypatch.setattr("lg_app.backend_client.create_order", fake_create_order)
    state = make_state("I want to order two different products")

    result = order_agent(state)

    assert calls == []
    assert result["response"] == "Which 2 products would you like to order?"


def test_order_agent_handles_catalog_position_quantities_across_details_turn(monkeypatch):
    calls = []

    def fake_create_order(payload):
        calls.append(payload)
        return {"message": "Order created successfully", "total_price": 798}

    monkeypatch.setattr("lg_app.backend_client.create_order", fake_create_order)
    state = make_state("I need to order two items for the first product and >5 on product 2")
    state["last_catalog_products"] = ["Hair Oil", "Face Cream"]

    pending = order_agent(state)

    assert calls == []
    assert pending["pending_order_json"]["items"] == [
        {"product_id": "prod-123", "quantity": 2},
        {"product_id": "prod-456", "quantity": 5},
    ]
    assert pending["response"] == "Please send name, phone, city, delivery address."

    pending["message"] = "name: tom, phone: 0661612345, city: rabat, delivery address: rabat ville"
    created = order_agent(pending)

    assert calls[0]["items"] == [
        {"product_id": "prod-123", "quantity": 2},
        {"product_id": "prod-456", "quantity": 5},
    ]
    assert "Total: 798 MAD" in created["response"]


def test_order_agent_handles_product_number_quantities_with_in_preposition(monkeypatch):
    calls = []

    def fake_create_order(payload):
        calls.append(payload)
        return {"message": "Order created successfully", "total_price": 339}

    monkeypatch.setattr("lg_app.backend_client.create_order", fake_create_order)
    state = make_state(
        "i need to order 1 product 1 and 2 in product 2, name: tom, phone: 0661612345, city: rabat, delivery address: rabat ville"
    )
    state["last_catalog_products"] = ["Hair Oil", "Face Cream"]

    order_agent(state)

    assert calls[0]["items"] == [
        {"product_id": "prod-123", "quantity": 1},
        {"product_id": "prod-456", "quantity": 2},
    ]


def test_order_agent_handles_partial_product_names_with_quantities(monkeypatch):
    calls = []

    def fake_create_order(payload):
        calls.append(payload)
        return {"message": "Order created successfully", "total_price": 3000}

    monkeypatch.setattr("lg_app.backend_client.create_order", fake_create_order)
    state = make_state(
        "i need to order two mac and one apple, name: tom, phone: 0661612345, city: rabat, delivery address: rabat ville",
        active_product_id=None,
    )
    state["shop_data"] = [
        {
            "id": "prod-mac",
            "name": "MacBook Pro",
            "price": 1000,
            "available": True,
            "stock": 4,
        },
        {
            "id": "prod-apple",
            "name": "Apple Watch",
            "price": 1000,
            "available": True,
            "stock": 4,
        },
    ]

    order_agent(state)

    assert calls[0]["items"] == [
        {"product_id": "prod-mac", "quantity": 2},
        {"product_id": "prod-apple", "quantity": 1},
    ]


def test_product_change_clears_pending_order_quantity():
    state = make_state("tell me about Face Cream")
    state["active_product"] = "Hair Oil"
    state["active_product_id"] = "prod-123"
    state["active_product_name"] = "Hair Oil"
    state["current_product_id"] = "prod-123"
    state["product_query"] = "Face Cream"
    state["pending_order_json"] = {
        "quantity": 2,
        "customer_info": {"name": "tom"},
    }

    result = update_active_product(state)

    assert result["active_product_id"] == "prod-456"
    assert result["pending_order_json"] is None


def test_missing_active_product_id_asks_product_question(monkeypatch):
    def fail_create_order(payload):
        raise AssertionError("backend should not be called")

    monkeypatch.setattr("lg_app.backend_client.create_order", fail_create_order)
    state = make_state(
        "name: tom, phone: 0661612345, city: rabat, delivery address: rabat ville",
        active_product_id=None,
    )

    result = order_agent(state)

    assert result["response"] == "Which product would you like to order?"


def test_missing_customer_fields_asks_only_for_missing_fields(monkeypatch):
    def fail_create_order(payload):
        raise AssertionError("backend should not be called")

    monkeypatch.setattr("lg_app.backend_client.create_order", fail_create_order)
    state = make_state("name: tom, phone: 0661612345")

    result = order_agent(state)

    assert result["response"] == "Please send city, delivery address."
    assert result["pending_order_json"]["customer_info"] == {
        "name": "tom",
        "phone": "0661612345",
    }


def test_router_classifies_order_creation_keywords_and_fields():
    for message in [
        "I want to order",
        "I want to buy",
        "place order",
        "confirm order",
        "checkout",
        "name: tom",
        "phone: 0661612345",
        "city: rabat",
        "delivery address: rabat ville",
        "address: rabat ville",
    ]:
        result = deterministic_intent_router(make_state(message))
        assert result["intent"] == "order_creation", message


def test_router_classifies_short_order_tracking_questions():
    for message in [
        "when my order",
        "when is my order",
        "where my order",
        "when will my order arrive",
        "order tracking",
        "what is the final price of my order",
        "give me more details about order",
        "give me more details about my order",
    ]:
        result = deterministic_intent_router(make_state(message))
        assert result["intent"] == "order_status", message
