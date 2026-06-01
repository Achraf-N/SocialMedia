"""Backend integration smoke test for POST /api/owner/chat."""

from pathlib import Path
import sys
from datetime import datetime, timezone

from bson import ObjectId
from fastapi.testclient import TestClient


ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
LANGGRAPH_DIR = ROOT_DIR / "langgraph"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(LANGGRAPH_DIR))

from app.core.dependencies import get_current_owner
from app.core.database import owners_collection, products_collection, shops_collection
from app.main import app
from owner.owner_memory import owner_sessions
from owner.nodes import owner_router


AUTH_OWNER_ID = ObjectId("64f000000000000000000001")
OTHER_OWNER_ID = ObjectId("64f000000000000000000002")
SHOP_ID = ObjectId("64f000000000000000000101")
OTHER_SHOP_ID = ObjectId("64f000000000000000000102")
PRODUCT_ID = ObjectId("64f000000000000000000201")


def now():
    return datetime.now(timezone.utc)


def seed_data():
    cleanup_data()
    owners_collection.insert_many(
        [
            {
                "_id": AUTH_OWNER_ID,
                "email": "owner@example.com",
                "name": "Owner",
                "hashed_password": "x",
                "created_at": now(),
                "updated_at": now(),
            },
            {
                "_id": OTHER_OWNER_ID,
                "email": "other@example.com",
                "name": "Other Owner",
                "hashed_password": "x",
                "created_at": now(),
                "updated_at": now(),
            },
        ]
    )
    shops_collection.insert_many(
        [
            {
                "_id": SHOP_ID,
                "owner_id": AUTH_OWNER_ID,
                "name": "Beauty Shop Casa",
                "delivery": "Casablanca 25 MAD",
                "created_at": now(),
                "updated_at": now(),
            },
            {
                "_id": OTHER_SHOP_ID,
                "owner_id": OTHER_OWNER_ID,
                "name": "Hidden Other Shop",
                "delivery": "Rabat 25 MAD",
                "created_at": now(),
                "updated_at": now(),
            },
        ]
    )
    products_collection.insert_one(
        {
            "_id": PRODUCT_ID,
            "owner_id": AUTH_OWNER_ID,
            "shop_id": SHOP_ID,
            "name": "Hair Oil",
            "price": 99,
            "description": "Natural oil",
            "available": True,
            "category": "Hair Care",
            "stock": 10,
            "delivery_time": "24-48h",
            "brand": "BeautyCare",
            "variants": [],
            "image": "",
            "created_at": now(),
            "updated_at": now(),
        }
    )


def cleanup_data():
    owners_collection.delete_many({"_id": {"$in": [AUTH_OWNER_ID, OTHER_OWNER_ID]}})
    shops_collection.delete_many({"_id": {"$in": [SHOP_ID, OTHER_SHOP_ID]}})
    products_collection.delete_many({"_id": PRODUCT_ID})


def install_router_fallback():
    original = owner_router.route_with_llm
    owner_router.route_with_llm = lambda state, use_llm=False: None
    return original


def restore_router(original):
    owner_router.route_with_llm = original


def fake_current_owner():
    return {"_id": AUTH_OWNER_ID, "email": "owner@example.com", "name": "Owner"}


def run_tests():
    seed_data()
    owner_sessions.pop(str(AUTH_OWNER_ID), None)
    original_router = install_router_fallback()
    app.dependency_overrides[get_current_owner] = fake_current_owner
    client = TestClient(app)

    try:
        shops_response = client.post(
            "/api/owner/chat",
            json={"message": "show my shops", "owner_id": "frontend-must-be-ignored"},
        )
        assert shops_response.status_code == 200, shops_response.text
        shops_json = shops_response.json()
        assert shops_json["intent"] == "list_shops", shops_json
        assert "Beauty Shop Casa" in shops_json["response"], shops_json
        assert "Hidden Other Shop" not in shops_json["response"], shops_json

        select_response = client.post("/api/owner/chat", json={"message": "select Beauty Shop Casa"})
        assert select_response.status_code == 200, select_response.text
        select_json = select_response.json()
        assert select_json["intent"] == "select_shop", select_json
        assert select_json["selected_shop_id"] == str(SHOP_ID), select_json
        assert select_json["current_shop_id"] == str(SHOP_ID), select_json

        products_response = client.post("/api/owner/chat", json={"message": "show products"})
        assert products_response.status_code == 200, products_response.text
        products_json = products_response.json()
        assert products_json["intent"] == "list_products", products_json
        assert products_json["current_shop_id"] == str(SHOP_ID), products_json
        assert "Hair Oil" in products_json["response"], products_json

        print("owner chat backend integration test passed")
    finally:
        app.dependency_overrides.pop(get_current_owner, None)
        restore_router(original_router)
        owner_sessions.pop(str(AUTH_OWNER_ID), None)
        cleanup_data()


if __name__ == "__main__":
    run_tests()
