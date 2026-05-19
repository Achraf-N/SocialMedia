"""Backend client for the owner management agent."""

import os
from typing import Any

import requests


BACKEND_BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def _safe_request(method: str, path: str, **kwargs) -> Any:
    url = f"{BACKEND_BASE_URL}{path}"
    try:
        response = requests.request(method, url, timeout=8, **kwargs)
        response.raise_for_status()
        if response.content:
            return response.json()
        return {"ok": True}
    except requests.HTTPError as exc:
        detail = "Backend request failed."
        if exc.response is not None:
            try:
                detail = str(exc.response.json().get("detail") or detail)
            except ValueError:
                detail = exc.response.text[:240] or detail
        return {"ok": False, "error": detail}
    except requests.RequestException:
        return {"ok": False, "error": "Backend service is not reachable right now."}


def get_owner_shops(owner_id):
    return _safe_request("GET", f"/api/owners/{owner_id}/shops")


def get_shop_products(shop_id):
    return _safe_request("GET", f"/api/shops/{shop_id}/products")


def create_product(shop_id, product_data):
    return _safe_request("POST", f"/api/shops/{shop_id}/products", json=product_data)


def update_product(shop_id, product_id, update_data):
    return _safe_request("PATCH", f"/api/shops/{shop_id}/products/{product_id}", json=update_data)


def update_product_stock(shop_id, product_id, stock_update):
    return _safe_request("PATCH", f"/api/shops/{shop_id}/products/{product_id}/stock", json=stock_update)


def update_product_price(shop_id, product_id, price):
    return _safe_request("PATCH", f"/api/shops/{shop_id}/products/{product_id}", json={"price": price})


def get_shop_orders(shop_id, status=None):
    params = {"status": status} if status else None
    return _safe_request("GET", f"/api/shops/{shop_id}/orders", params=params)


def update_order_status(order_id, status):
    return _safe_request("PATCH", f"/api/orders/{order_id}/status", json={"status": status})
