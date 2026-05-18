from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import orders_collection, products_collection, shops_collection
from app.core.dependencies import get_current_owner, get_owned_shop
from app.models.common import now_utc
from app.models.order_model import (
    OrderCreate,
    OrderDetailWithShopResponse,
    OrderListWithShopResponse,
    OrderResponse,
    OrderUpdate,
    PublicOrderCreate,
)
from app.views.serializers import serialize_document

router = APIRouter(prefix="/shops/{shop_id}/orders", tags=["orders"])


def _get_owned_product(product_id: str, owner: dict, shop: dict) -> dict:
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product id")
    product = products_collection.find_one(
        {"_id": ObjectId(product_id), "owner_id": owner["_id"], "shop_id": shop["_id"]}
    )
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


def _delivery_summary(shop: dict, city: str) -> str:
    delivery = shop.get("delivery")
    if delivery:
        return f"Delivery to {city}: {delivery}"
    return "Delivery information is not available yet."


def _fetch_products_map(orders: list[dict]) -> dict:
    """Batch-fetch all products referenced in a list of orders."""
    ids = list({item["product_id"] for o in orders for item in o.get("items", [])})
    if not ids:
        return {}
    return {p["_id"]: p for p in products_collection.find({"_id": {"$in": ids}})}


def _serialize_order(order: dict, products_map: dict, shop_name: str = "") -> dict:
    """Serialize an order document with enriched item details."""
    items = []
    for item in order.get("items", []):
        pid = item["product_id"]
        product = products_map.get(pid)
        unit_price = float(product.get("price", 0)) if product else 0.0
        qty = item["quantity"]
        items.append({
            "product_id": str(pid),
            "product_name": product.get("name") if product else None,
            "quantity": qty,
            "unit_price": unit_price,
            "total_price": unit_price * qty,
        })
    return {
        "id": str(order["_id"]),
        "session_id": str(order["session_id"]) if order.get("session_id") else None,
        "shop_id": str(order["shop_id"]),
        "shop_name": shop_name or None,
        "items": items,
        "total_price": float(order.get("total_price", 0)),
        "status": order.get("status", "pending"),
        "customer_info": order.get("customer_info", {}),
        "created_at": order["created_at"],
        "updated_at": order["updated_at"],
    }


@router.post("/public", status_code=status.HTTP_201_CREATED)
def create_public_order(shop_id: str, order_in: PublicOrderCreate) -> dict:
    """Create a customer order via the public chatbot endpoint (LangGraph format)."""
    if not ObjectId.is_valid(shop_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid shop id")
    if not ObjectId.is_valid(order_in.product_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product id")

    shop = shops_collection.find_one({"_id": ObjectId(shop_id)})
    if not shop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")

    product = products_collection.find_one(
        {"_id": ObjectId(order_in.product_id), "shop_id": shop["_id"]}
    )
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if product.get("available") is not True or product.get("stock", 0) < order_in.quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product is not available or out of stock")

    unit_price = float(product.get("price", 0))
    total_price = unit_price * order_in.quantity
    now = now_utc()
    order = {
        "session_id": None,
        "shop_id": shop["_id"],
        "items": [
            {
                "product_id": product["_id"],
                "quantity": order_in.quantity,
            }
        ],
        "total_price": total_price,
        "status": "pending",
        "customer_info": {
            "name": order_in.customer_name,
            "phone": order_in.customer_phone,
            "city": order_in.city,
            "delivery_address": order_in.address,
        },
        "created_at": now,
        "updated_at": now,
    }
    result = orders_collection.insert_one(order)

    return {
        "order_id": str(result.inserted_id),
        "status": "pending",
        "product": serialize_document(product),
        "quantity": order_in.quantity,
        "total_price": total_price,
        "delivery": _delivery_summary(shop, order_in.city),
    }


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    shop_id: str,
    order_in: OrderCreate,
    owner: dict = Depends(get_current_owner),
) -> dict:
    shop = get_owned_shop(shop_id, owner)

    items_to_insert = []
    total_price = 0.0

    for item in order_in.items:
        product = _get_owned_product(item.product_id, owner, shop)
        if product.get("available") is not True or product.get("stock", 0) < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product '{product.get('name')}' is not available or out of stock",
            )
        unit_price = float(product.get("price", 0))
        total_price += unit_price * item.quantity
        items_to_insert.append({
            "product_id": product["_id"],
            "quantity": item.quantity,
        })

    now = now_utc()
    order = {
        "session_id": ObjectId(order_in.session_id) if order_in.session_id and ObjectId.is_valid(order_in.session_id) else None,
        "shop_id": shop["_id"],
        "items": items_to_insert,
        "total_price": total_price,
        "status": "pending",
        "customer_info": order_in.customer_info.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    result = orders_collection.insert_one(order)
    created = orders_collection.find_one({"_id": result.inserted_id})
    products_map = _fetch_products_map([created])
    return _serialize_order(created, products_map, shop.get("name", ""))


@router.get("", response_model=OrderListWithShopResponse)
def list_orders(
    shop_id: str,
    owner: dict = Depends(get_current_owner),
) -> dict:
    shop = get_owned_shop(shop_id, owner)
    orders = list(
        orders_collection.find({"shop_id": shop["_id"]}).sort("created_at", -1)
    )
    products_map = _fetch_products_map(orders)
    shop_name = shop.get("name", "")
    enriched = [_serialize_order(o, products_map, shop_name) for o in orders]
    return {"shop": serialize_document(shop), "orders": enriched}


@router.get("/{order_id}", response_model=OrderDetailWithShopResponse)
def get_order(
    shop_id: str,
    order_id: str,
    owner: dict = Depends(get_current_owner),
) -> dict:
    shop = get_owned_shop(shop_id, owner)
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object id")

    order = orders_collection.find_one({"_id": ObjectId(order_id), "shop_id": shop["_id"]})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    products_map = _fetch_products_map([order])
    return {"shop": serialize_document(shop), "order": _serialize_order(order, products_map, shop.get("name", ""))}


@router.patch("/{order_id}", response_model=OrderResponse)
def update_order(
    shop_id: str,
    order_id: str,
    order_in: OrderUpdate,
    owner: dict = Depends(get_current_owner),
) -> dict:
    shop = get_owned_shop(shop_id, owner)
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object id")

    update_data = order_in.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    update_data["updated_at"] = now_utc()
    result = orders_collection.update_one(
        {"_id": ObjectId(order_id), "shop_id": shop["_id"]},
        {"$set": update_data},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    updated = orders_collection.find_one({"_id": ObjectId(order_id)})
    products_map = _fetch_products_map([updated])
    return _serialize_order(updated, products_map, shop.get("name", ""))


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    shop_id: str,
    order_id: str,
    owner: dict = Depends(get_current_owner),
) -> None:
    shop = get_owned_shop(shop_id, owner)
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object id")

    result = orders_collection.delete_one({"_id": ObjectId(order_id), "shop_id": shop["_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
