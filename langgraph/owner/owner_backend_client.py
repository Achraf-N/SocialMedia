"""Backend client for the owner management agent."""

from contextvars import ContextVar
import os
from typing import Any

import requests
from bson import ObjectId


BACKEND_BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
_CURRENT_OWNER_ID: ContextVar[str | None] = ContextVar("owner_agent_current_owner_id", default=None)


def set_current_owner_id(owner_id: str | None):
    return _CURRENT_OWNER_ID.set(owner_id)


def reset_current_owner_id(token) -> None:
    _CURRENT_OWNER_ID.reset(token)


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


def _internal_owner_id(owner_id: str | None = None) -> ObjectId | None:
    candidate = owner_id or _CURRENT_OWNER_ID.get()
    if candidate and ObjectId.is_valid(candidate):
        return ObjectId(candidate)
    return None


def _backend_modules():
    try:
        from app.core.database import orders_collection, products_collection, shops_collection
        from app.models.common import now_utc
        from app.views.serializers import serialize_document, serialize_documents, serialize_product, serialize_products

        return {
            "orders": orders_collection,
            "products": products_collection,
            "shops": shops_collection,
            "now": now_utc,
            "serialize_document": serialize_document,
            "serialize_documents": serialize_documents,
            "serialize_product": serialize_product,
            "serialize_products": serialize_products,
        }
    except Exception:
        return None


def _get_owned_shop(shop_id: str, owner_id: ObjectId, modules: dict) -> dict | None:
    if not ObjectId.is_valid(shop_id):
        return None
    return modules["shops"].find_one({"_id": ObjectId(shop_id), "owner_id": owner_id})


def _find_product(shop_id: str, product_id: str, owner_id: ObjectId, modules: dict) -> dict | None:
    shop = _get_owned_shop(shop_id, owner_id, modules)
    if not shop:
        return None

    query: dict[str, Any] = {"shop_id": shop["_id"], "owner_id": owner_id}
    if ObjectId.is_valid(str(product_id)):
        query["_id"] = ObjectId(str(product_id))
    else:
        query["name"] = {"$regex": f"^{str(product_id)}$", "$options": "i"}
    return modules["products"].find_one(query)


def get_owner_shops(owner_id):
    modules = _backend_modules()
    owner_obj_id = _internal_owner_id(owner_id)
    if modules and owner_obj_id:
        shops = list(modules["shops"].find({"owner_id": owner_obj_id}).sort("created_at", -1))
        return {"shops": modules["serialize_documents"](shops)}
    return _safe_request("GET", "/api/shops/me")


def get_shop_products(shop_id):
    modules = _backend_modules()
    owner_obj_id = _internal_owner_id()
    if modules and owner_obj_id:
        shop = _get_owned_shop(shop_id, owner_obj_id, modules)
        if not shop:
            return {"ok": False, "error": "Shop not found"}
        products = list(modules["products"].find({"shop_id": shop["_id"], "owner_id": owner_obj_id}).sort("created_at", -1))
        return {"shop": modules["serialize_document"](shop), "products": modules["serialize_products"](products)}
    return _safe_request("GET", f"/api/shops/{shop_id}/products")


def create_product(shop_id, product_data):
    modules = _backend_modules()
    owner_obj_id = _internal_owner_id()
    if modules and owner_obj_id:
        shop = _get_owned_shop(shop_id, owner_obj_id, modules)
        if not shop:
            return {"ok": False, "error": "Shop not found"}
        now = modules["now"]()
        product = {
            **product_data,
            "image": product_data.get("image") or "",
            "owner_id": owner_obj_id,
            "shop_id": shop["_id"],
            "created_at": now,
            "updated_at": now,
        }
        result = modules["products"].insert_one(product)
        created = modules["products"].find_one({"_id": result.inserted_id})
        return {"message": "Product created.", "product": modules["serialize_product"](created)}
    return _safe_request("POST", f"/api/shops/{shop_id}/products", json=product_data)


def update_product(shop_id, product_id, update_data):
    modules = _backend_modules()
    owner_obj_id = _internal_owner_id()
    if modules and owner_obj_id:
        product = _find_product(shop_id, product_id, owner_obj_id, modules)
        if not product:
            return {"ok": False, "error": "Product not found"}
        update_data = {key: value for key, value in update_data.items() if value is not None}
        if not update_data:
            return {"ok": False, "error": "No fields to update"}
        update_data["updated_at"] = modules["now"]()
        modules["products"].update_one({"_id": product["_id"]}, {"$set": update_data})
        updated = modules["products"].find_one({"_id": product["_id"]})
        return {"message": "Product updated.", "product": modules["serialize_product"](updated)}
    return _safe_request("PATCH", f"/api/shops/{shop_id}/products/{product_id}", json=update_data)


def get_product(shop_id, product_id):
    modules = _backend_modules()
    owner_obj_id = _internal_owner_id()
    if modules and owner_obj_id:
        product = _find_product(shop_id, product_id, owner_obj_id, modules)
        if not product:
            return {"ok": False, "error": "Product not found"}
        return {"product": modules["serialize_product"](product)}
    return _safe_request("GET", f"/api/shops/{shop_id}/products/{product_id}")


def delete_product(shop_id, product_id):
    modules = _backend_modules()
    owner_obj_id = _internal_owner_id()
    if modules and owner_obj_id:
        product = _find_product(shop_id, product_id, owner_obj_id, modules)
        if not product:
            return {"ok": False, "error": "Product not found"}
        modules["products"].delete_one({"_id": product["_id"]})
        return {"message": "Product deleted.", "product": modules["serialize_product"](product)}
    return _safe_request("DELETE", f"/api/shops/{shop_id}/products/{product_id}")


def update_product_stock(shop_id, product_id, stock_update):
    modules = _backend_modules()
    owner_obj_id = _internal_owner_id()
    if modules and owner_obj_id:
        product = _find_product(shop_id, product_id, owner_obj_id, modules)
        if not product:
            return {"ok": False, "error": "Product not found"}
        operation = stock_update.get("operation")
        quantity = int(stock_update.get("quantity", 0))
        current_stock = int(product.get("stock", 0))
        if operation == "set":
            new_stock = quantity
        elif operation == "increase":
            new_stock = current_stock + quantity
        elif operation == "decrease":
            new_stock = max(0, current_stock - quantity)
        else:
            return {"ok": False, "error": "Invalid stock operation"}
        modules["products"].update_one(
            {"_id": product["_id"]},
            {"$set": {"stock": new_stock, "available": new_stock > 0, "updated_at": modules["now"]()}},
        )
        updated = modules["products"].find_one({"_id": product["_id"]})
        return {"message": "Stock updated.", "product": modules["serialize_product"](updated)}
    return _safe_request("PATCH", f"/api/shops/{shop_id}/products/{product_id}/stock", json=stock_update)


def update_product_price(shop_id, product_id, price):
    modules = _backend_modules()
    owner_obj_id = _internal_owner_id()
    if modules and owner_obj_id:
        product = _find_product(shop_id, product_id, owner_obj_id, modules)
        if not product:
            return {"ok": False, "error": "Product not found"}
        modules["products"].update_one(
            {"_id": product["_id"]},
            {"$set": {"price": price, "updated_at": modules["now"]()}},
        )
        updated = modules["products"].find_one({"_id": product["_id"]})
        return {"message": "Price updated.", "product": modules["serialize_product"](updated)}
    return _safe_request("PATCH", f"/api/shops/{shop_id}/products/{product_id}", json={"price": price})


def get_shop_orders(shop_id, status=None):
    modules = _backend_modules()
    owner_obj_id = _internal_owner_id()
    if modules and owner_obj_id:
        shop = _get_owned_shop(shop_id, owner_obj_id, modules)
        if not shop:
            return {"ok": False, "error": "Shop not found"}
        query: dict[str, Any] = {"shop_id": shop["_id"]}
        if status:
            query["status"] = status
        orders = list(modules["orders"].find(query).sort("created_at", -1))
        return {"shop": modules["serialize_document"](shop), "orders": modules["serialize_documents"](orders)}
    params = {"status": status} if status else None
    return _safe_request("GET", f"/api/shops/{shop_id}/orders", params=params)


def update_order_status(order_id, status):
    modules = _backend_modules()
    owner_obj_id = _internal_owner_id()
    if modules and owner_obj_id:
        if not ObjectId.is_valid(str(order_id)):
            return {"ok": False, "error": "Invalid order id"}
        order = modules["orders"].find_one({"_id": ObjectId(str(order_id))})
        if not order:
            return {"ok": False, "error": "Order not found"}
        shop = modules["shops"].find_one({"_id": order.get("shop_id"), "owner_id": owner_obj_id})
        if not shop:
            return {"ok": False, "error": "Order not found"}
        modules["orders"].update_one(
            {"_id": order["_id"]},
            {"$set": {"status": status, "updated_at": modules["now"]()}},
        )
        updated = modules["orders"].find_one({"_id": order["_id"]})
        return {"message": "Order status updated.", "order": modules["serialize_document"](updated)}
    return _safe_request("PATCH", f"/api/orders/{order_id}/status", json={"status": status})
