"""Scenario tests for the Nike/Adidas seeded shop."""

from pathlib import Path
import sys

from bson import ObjectId
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent / "langgraph"))

from app.core.database import chat_sessions_collection, products_collection, shops_collection
from app.main import app


SHOP_ID = "6a0a539fc366cec4522119c7"
client = TestClient(app)


def assert_shop_exists() -> None:
    assert ObjectId.is_valid(SHOP_ID), "Sports shop id is not a valid ObjectId"
    shop = shops_collection.find_one({"_id": ObjectId(SHOP_ID)})
    assert shop, f"Shop {SHOP_ID} not found"
    products = list(products_collection.find({"shop_id": ObjectId(SHOP_ID)}))
    names = {p["name"] for p in products}
    expected = {
        "Nike Air Max 270",
        "Nike Dri-FIT Training T-Shirt",
        "Adidas Ultraboost Light",
        "Adidas Essentials Hoodie",
    }
    assert expected.issubset(names), names


def chat(session_id: str, message: str) -> dict:
    response = client.post(
        "/api/chat",
        json={"message": message, "session_id": session_id, "shop_id": SHOP_ID},
    )
    assert response.status_code == 200, response.text
    return response.json()


def assert_contains(text: str, *parts: str) -> None:
    lowered = text.lower()
    for part in parts:
        assert part.lower() in lowered, text


if __name__ == "__main__":
    assert_shop_exists()

    # Start clean so memory from manual chat does not affect expectations.
    chat_sessions_collection.delete_many({"shop_id": SHOP_ID})

    catalog = client.get(f"/api/shops/{SHOP_ID}/products")
    assert catalog.status_code == 200, catalog.text
    catalog_json = catalog.json()
    assert catalog_json["shop"]["name"] == "Nike Adidas Sports Store"
    assert len(catalog_json["products"]) == 4

    result = chat("sports-catalog", "what products do you have?")
    assert result["intent"] == "product_list", result
    assert result["current_product"] is None, result
    assert_contains(
        result["response"],
        "Nike Air Max 270",
        "Nike Dri-FIT Training T-Shirt",
        "Adidas Ultraboost Light",
        "Adidas Essentials Hoodie",
    )

    nike = chat("sports-brand-nike", "give me more details about Nike")
    assert nike["intent"] == "product_list", nike
    assert nike["current_product"] is None, nike
    assert_contains(nike["response"], "Nike Air Max 270", "Nike Dri-FIT")
    assert "Adidas Ultraboost" not in nike["response"], nike

    adidas = chat("sports-brand-adidas", "show me Adidas products")
    assert adidas["intent"] == "product_list", adidas
    assert adidas["current_product"] is None, adidas
    assert_contains(adidas["response"], "Adidas Ultraboost Light", "Adidas Essentials Hoodie")
    assert "Nike Air Max" not in adidas["response"], adidas

    details = chat("sports-specific", "tell me more about Nike Air Max 270")
    assert details["intent"] == "product_info_question", details
    assert details["current_product"] == "Nike Air Max 270", details
    assert_contains(details["response"], "Nike Air Max 270")

    follow_price = chat("sports-specific", "how much is it?")
    assert follow_price["intent"] == "price_question", follow_price
    assert follow_price["current_product"] == "Nike Air Max 270", follow_price
    assert_contains(follow_price["response"], "1299")

    expensive = chat("sports-expensive", "give me the expensive one")
    assert expensive["intent"] == "product_list", expensive
    assert expensive["current_product"] == "Adidas Ultraboost Light", expensive
    assert_contains(expensive["response"], "Adidas Ultraboost Light", "1499")

    expensive_follow = chat("sports-expensive", "can you deliver it to Casablanca?")
    assert expensive_follow["intent"] == "delivery_question", expensive_follow
    assert expensive_follow["current_product"] == "Adidas Ultraboost Light", expensive_follow
    assert expensive_follow["delivery_city"] == "Casablanca", expensive_follow

    cheapest = chat("sports-cheapest", "give me the cheapest one")
    assert cheapest["intent"] == "product_list", cheapest
    assert cheapest["current_product"] == "Nike Dri-FIT Training T-Shirt", cheapest
    assert_contains(cheapest["response"], "Nike Dri-FIT Training T-Shirt", "349")

    other_prices = chat("sports-cheapest", "give me the price for all other products")
    assert other_prices["intent"] == "product_list", other_prices
    assert "Nike Dri-FIT Training T-Shirt: 349 MAD" not in other_prices["response"], other_prices
    assert_contains(other_prices["response"], "Nike Air Max 270", "Adidas Ultraboost Light")
    assert other_prices["delivery_city"] is None, other_prices

    payment = chat("sports-payment", "Can I pay cash on delivery?")
    assert payment["intent"] == "payment_question", payment
    assert_contains(payment["response"], "cash")

    delivery = chat("sports-delivery", "How much is delivery to Rabat?")
    assert delivery["intent"] == "delivery_question", delivery
    assert delivery["delivery_city"] == "Rabat", delivery
    assert_contains(delivery["response"], "Rabat")

    order_start = chat("sports-order", "I want to order Adidas Essentials Hoodie")
    assert order_start["intent"] == "order_intent", order_start
    assert order_start["current_product"] == "Adidas Essentials Hoodie", order_start
    assert_contains(order_start["response"], "I just need")

    # Changing topic while an order is pending should not stay stuck in order mode.
    switch_topic = chat("sports-order", "how much is Nike Air Max 270?")
    assert switch_topic["intent"] == "price_question", switch_topic
    assert switch_topic["current_product"] == "Nike Air Max 270", switch_topic

    cancel_order = chat("sports-cancel-order", "I want to order Nike Air Max 270")
    assert cancel_order["intent"] == "order_intent", cancel_order
    cancelled = chat("sports-cancel-order", "cancel")
    assert cancelled["intent"] == "order_intent", cancelled
    assert_contains(cancelled["response"], "cancelled")

    chain_session = "sports-human-like-chain"
    chat_sessions_collection.delete_many({"session_id": chain_session, "shop_id": SHOP_ID})
    shop_name = chat(chain_session, "what is shop name")
    assert shop_name["intent"] == "shop_info_question", shop_name
    assert_contains(shop_name["response"], "Nike Adidas Sports Store")

    products = chat(chain_session, "what are the products?")
    assert products["intent"] == "product_list", products
    assert products["current_product"] is None, products

    product_one = chat(chain_session, "what is the details product 1")
    assert product_one["intent"] == "product_info_question", product_one
    assert product_one["current_product"] == "Nike Air Max 270", product_one

    brand = chat(chain_session, "what is brand then the product")
    assert brand["intent"] == "product_info_question", brand
    assert brand["current_product"] == "Nike Air Max 270", brand
    assert_contains(brand["response"], "Nike")

    order_it = chat(chain_session, "I want to order it")
    assert order_it["intent"] == "order_intent", order_it
    assert order_it["current_product"] == "Nike Air Max 270", order_it
    assert_contains(order_it["response"], "I just need")

    partial_order = chat(chain_session, "name:x, phone:999, address: ad")
    assert partial_order["intent"] == "order_intent", partial_order
    assert partial_order["current_product"] == "Nike Air Max 270", partial_order
    assert_contains(partial_order["response"], "valid phone number", "city")

    print("All sports shop scenarios passed")
