"""Production-flow smoke tests for product API, memory, delivery, and orders."""

from datetime import datetime, timezone
from pathlib import Path
import sys

from bson import ObjectId
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import (
    chat_sessions_collection,
    orders_collection,
    owners_collection,
    products_collection,
    shops_collection,
)
from app.main import app


client = TestClient(app)


def now():
    return datetime.now(timezone.utc)


def seed_shop():
    owner_id = ObjectId()
    shop_id = ObjectId()
    owners_collection.insert_one(
        {
            "_id": owner_id,
            "email": f"test-{owner_id}@example.com",
            "name": "Test Owner",
            "hashed_password": "x",
            "created_at": now(),
            "updated_at": now(),
        }
    )
    shops_collection.insert_one(
        {
            "_id": shop_id,
            "owner_id": owner_id,
            "name": "Beauty Shop Casa",
            "delivery": "Casablanca 25 MAD, other cities 35 MAD, delivery in 24-72h",
            "payment": "Cash on delivery is available.",
            "created_at": now(),
            "updated_at": now(),
        }
    )
    products_collection.insert_many(
        [
            {
                "owner_id": owner_id,
                "shop_id": shop_id,
                "name": "Hair Oil",
                "price": 99,
                "description": "Natural oil for dry hair",
                "available": True,
                "category": "Hair Care",
                "stock": 12,
                "delivery_time": "24-48h",
                "brand": "BeautyCare",
                "variants": ["100ml", "200ml"],
                "image": "https://example.com/hair-oil.jpg",
                "created_at": now(),
                "updated_at": now(),
            },
            {
                "owner_id": owner_id,
                "shop_id": shop_id,
                "name": "Face Cream",
                "price": 120,
                "description": "Hydrating face cream",
                "available": False,
                "category": "Skin Care",
                "stock": 0,
                "delivery_time": "3-5 days",
                "brand": "PureGlow",
                "variants": ["50ml"],
                "image": "https://example.com/face-cream.jpg",
                "created_at": now(),
                "updated_at": now(),
            },
        ]
    )
    return str(shop_id)


def cleanup(shop_id: str):
    shop_obj_id = ObjectId(shop_id)
    shop = shops_collection.find_one({"_id": shop_obj_id})
    if shop:
        owners_collection.delete_one({"_id": shop["owner_id"]})
    shops_collection.delete_one({"_id": shop_obj_id})
    products_collection.delete_many({"shop_id": shop_obj_id})
    orders_collection.delete_many({"shop_id": shop_obj_id})
    chat_sessions_collection.delete_many({"shop_id": shop_id})


def post_chat(shop_id: str, session_id: str, message: str) -> dict:
    response = client.post(
        "/api/chat",
        json={"shop_id": shop_id, "session_id": session_id, "message": message},
    )
    assert response.status_code == 200, response.text
    return response.json()


if __name__ == "__main__":
    shop_id = seed_shop()
    try:
        missing_shop_id = client.post(
            "/api/chat",
            json={"session_id": "missing-shop", "message": "hello"},
        )
        assert missing_shop_id.status_code == 422

        product_response = client.get(f"/api/shops/{shop_id}/products")
        assert product_response.status_code == 200, product_response.text
        catalog = product_response.json()
        assert "shop" in catalog
        assert "products" in catalog
        assert len(catalog["products"]) == 2
        hair_oil = next(p for p in catalog["products"] if p["name"] == "Hair Oil")
        assert hair_oil["price"] == 99
        assert hair_oil["stock"] == 12
        assert hair_oil["available"] is True
        assert hair_oil["delivery_time"] == "24-48h"
        assert hair_oil["variants"] == ["100ml", "200ml"]

        missing_shop = client.get(f"/api/shops/{ObjectId()}/products")
        assert missing_shop.status_code == 404
        assert missing_shop.json()["detail"] == "Shop not found"

        session_id = "prod-flow-memory"
        chat_sessions_collection.delete_many({"session_id": session_id, "shop_id": shop_id})
        first = post_chat(shop_id, session_id, "Is Hair Oil available?")
        assert first["intent"] == "availability_question", first
        assert first["current_product"] == "Hair Oil", first

        second = post_chat(shop_id, session_id, "How much is it?")
        assert second["intent"] == "price_question", second
        assert second["current_product"] == "Hair Oil", second

        delivery = post_chat(shop_id, session_id, "How much is delivery to Casablanca?")
        assert delivery["intent"] == "delivery_question", delivery
        assert delivery["delivery_city"] == "Casablanca", delivery
        assert "Casablanca" in delivery["response"], delivery

        order = post_chat(shop_id, "prod-flow-order", "I want to order Hair Oil")
        assert order["intent"] == "order_intent", order
        assert order["current_product"] == "Hair Oil", order
        assert "Please send" in order["response"], order

        unavailable = post_chat(shop_id, "prod-flow-out-stock", "I want to order Face Cream")
        assert unavailable["intent"] == "order_intent", unavailable
        assert unavailable["current_product"] == "Face Cream", unavailable
        assert "not available" in unavailable["response"], unavailable

        chat_sessions_collection.delete_many({"session_id": "prod-flow-persistent", "shop_id": shop_id})
        persisted_first = post_chat(shop_id, "prod-flow-persistent", "Is Hair Oil available?")
        assert persisted_first["current_product"] == "Hair Oil", persisted_first
        persisted = chat_sessions_collection.find_one(
            {"session_id": "prod-flow-persistent", "shop_id": shop_id}
        )
        assert persisted["active_product"] == "Hair Oil"
        second_after_reload = post_chat(shop_id, "prod-flow-persistent", "How much is it?")
        assert second_after_reload["current_product"] == "Hair Oil", second_after_reload

        print("All production flow tests passed")
    finally:
        cleanup(shop_id)
