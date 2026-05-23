"""Customer-router intent matrix using only stdlib unittest.

Run with:
    python -m unittest langgraph.test_customer_router_matrix
"""

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LANGGRAPH_DIR = PROJECT_ROOT / "langgraph"
sys.path.insert(0, str(LANGGRAPH_DIR))

from lg_app.nodes.router import _apply_sales_priority, deterministic_intent_router


PRODUCTS = [
    {
        "id": "prod-samba",
        "name": "Adidas Samba OG0",
        "brand": "Adidas",
        "category": "Sneakers",
        "price": 899,
        "available": True,
        "stock": 10,
    },
    {
        "id": "prod-ultra",
        "name": "Adidas Ultraboost Light",
        "brand": "Adidas",
        "category": "Running Shoes",
        "price": 1499,
        "available": True,
        "stock": 5,
    },
    {
        "id": "prod-nike",
        "name": "Nike Air Max 270",
        "brand": "Nike",
        "category": "Sneakers",
        "price": 1299,
        "available": True,
        "stock": 7,
    },
]


def make_state(
    message,
    *,
    active_product="Adidas Samba OG0",
    pending_order_json=None,
    last_catalog_products=None,
):
    active = next((p for p in PRODUCTS if p["name"] == active_product), None)
    active_id = active["id"] if active else None
    return {
        "session_id": "router-session",
        "shop_id": "shop-123",
        "message": message,
        "intent": None,
        "product_query": None,
        "active_product": active_product if active else None,
        "active_product_id": active_id,
        "active_product_name": active_product if active else None,
        "current_product_id": active_id,
        "current_product": active_product if active else None,
        "current_product_name": active_product if active else None,
        "delivery_city": None,
        "delivery_address": None,
        "pending_order_json": pending_order_json,
        "shop_info": None,
        "catalog_filter": None,
        "last_catalog_products": last_catalog_products,
        "response": None,
        "steps": [],
        "shop_data": PRODUCTS,
        "needs_human": False,
        "confidence": 0.0,
    }


def route(message, **state_kwargs):
    state = make_state(message, **state_kwargs)
    result = deterministic_intent_router(state)
    return _apply_sales_priority(state, result)


class CustomerRouterMatrixTest(unittest.TestCase):
    def assert_route(self, message, expected_intent, expected_product=None, **state_kwargs):
        with self.subTest(message=message):
            result = route(message, **state_kwargs)
            self.assertEqual(result["intent"], expected_intent)
            self.assertEqual(result["product_query"], expected_product)

    def test_common_customer_questions_route_to_expected_intents(self):
        cases = [
            ("hello", "greeting", None),
            ("thanks", "small_talk", None),
            ("what is shop name", "shop_info_question", None),
            ("what products do you have?", "product_list", None),
            ("show me Adidas products", "product_list", None),
            ("give me the cheapest one", "product_list", None),
            ("tell me more about Adidas Samba OG0", "product_info_question", "Adidas Samba OG0"),
            ("is Adidas Samba OG0 available?", "availability_question", "Adidas Samba OG0"),
            ("is it in stock?", "availability_question", "Adidas Samba OG0"),
            ("how much is Adidas Samba OG0?", "price_question", "Adidas Samba OG0"),
            ("how much is it?", "price_question", "Adidas Samba OG0"),
            ("can you deliver it to Casablanca?", "delivery_question", "Adidas Samba OG0"),
            ("how much is delivery to Rabat?", "delivery_question", None),
            ("Can I pay cash on delivery?", "payment_question", None),
            ("I want to order Adidas Samba OG0", "order_creation", "Adidas Samba OG0"),
            ("I need to order three Adidas Samba OG0", "order_creation", "Adidas Samba OG0"),
            ("name: achraf, phone: 0660606060, city: Rabat", "order_creation", "Adidas Samba OG0"),
            ("what is my order status?", "order_status", None),
            ("where is my order?", "order_status", None),
            ("where my order", "order_status", None),
            ("when my order", "order_status", None),
            ("when will my order arrive?", "order_status", None),
            ("order tracking", "order_status", None),
            ("I have a problem with my order", "complaint", None),
            ("I need support", "human_needed", None),
        ]

        for message, expected_intent, expected_product in cases:
            self.assert_route(message, expected_intent, expected_product)

    def test_catalog_index_references_use_last_catalog(self):
        self.assert_route(
            "first one please",
            "product_info_question",
            "Nike Air Max 270",
            last_catalog_products=["Nike Air Max 270", "Adidas Samba OG0"],
        )
        self.assert_route(
            "product 2 details",
            "product_info_question",
            "Adidas Samba OG0",
            last_catalog_products=["Nike Air Max 270", "Adidas Samba OG0"],
        )

    def test_pending_order_fields_stay_in_order_creation_but_tracking_does_not(self):
        pending = {"quantity": 3, "customer_info": {"name": "achraf"}}
        self.assert_route(
            "phone: 0660606060, city: Rabat",
            "order_creation",
            "Adidas Samba OG0",
            pending_order_json=pending,
        )
        self.assert_route(
            "when my order",
            "order_status",
            None,
            pending_order_json=pending,
        )


if __name__ == "__main__":
    unittest.main()
