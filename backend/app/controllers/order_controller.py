from bson import ObjectId
from fastapi import APIRouter, HTTPException, status

from app.core.database import orders_collection, products_collection, shops_collection
from app.models.common import now_utc
from app.models.order_model import (
    OrderCreate,
    OrderDetailWithShopResponse,
    OrderListWithShopResponse,
    OrderResponse,
    OrderStatusUpdate,
    OrderUpdate,
    PublicOrderCreate,
)
from app.views.serializers import serialize_document

router = APIRouter(prefix="/shops/{shop_id}/orders", tags=["orders"])
orders_router = APIRouter(prefix="/orders", tags=["orders"])


def _get_shop(shop_id: str) -> dict:
    if not ObjectId.is_valid(shop_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid shop id")
    shop = shops_collection.find_one({"_id": ObjectId(shop_id)})
    if not shop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")
    return shop


def _get_shop_product(product_id: str, shop: dict) -> dict:
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product id")
    product = products_collection.find_one(
        {"_id": ObjectId(product_id), "shop_id": shop["_id"]}
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


def _reserve_product_stock(product_filter: dict, quantity: int, detail: str) -> dict:
    """Atomically reduce product stock for an order item."""
    result = products_collection.update_one(
        {
            **product_filter,
            "available": True,
            "stock": {"$gte": quantity},
        },
        {
            "$inc": {"stock": -quantity},
            "$set": {"updated_at": now_utc()},
        },
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    product = products_collection.find_one(product_filter)
    if product and product.get("stock", 0) <= 0:
        products_collection.update_one(
            {"_id": product["_id"]},
            {"$set": {"available": False, "updated_at": now_utc()}},
        )
        product["available"] = False
    return product


def _restore_reserved_stock(reserved_items: list[tuple[ObjectId, int]]) -> None:
    """Best-effort rollback for stock already reserved before order creation failed."""
    for product_id, quantity in reserved_items:
        products_collection.update_one(
            {"_id": product_id},
            {
                "$inc": {"stock": quantity},
                "$set": {"available": True, "updated_at": now_utc()},
            },
        )


def _serialize_customer_info(order: dict) -> dict:
    """Normalize legacy and current customer fields for response validation."""
    customer_info = order.get("customer_info") or {}
    return {
        "name": customer_info.get("name") or order.get("customer_name") or "",
        "phone": customer_info.get("phone") or order.get("phone_number") or order.get("customer_phone") or "",
        "city": customer_info.get("city") or order.get("city") or "",
        "delivery_address": (
            customer_info.get("delivery_address")
            or order.get("delivery_address")
            or order.get("address")
            or ""
        ),
    }


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
        "customer_info": _serialize_customer_info(order),
        "created_at": order["created_at"],
        "updated_at": order["updated_at"],
    }


def _public_customer_info(order_in: PublicOrderCreate) -> dict:
    if order_in.customer_info is not None:
        return order_in.customer_info.model_dump()

    if order_in.customer_name and order_in.customer_phone and order_in.city and order_in.address:
        return {
            "name": order_in.customer_name,
            "phone": order_in.customer_phone,
            "city": order_in.city,
            "delivery_address": order_in.address,
        }

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="customer_info is required",
    )


def _create_public_order(shop_id: str, order_in: PublicOrderCreate) -> dict:
    shop = _get_shop(shop_id)
    raw_items = order_in.items or []
    if not raw_items:
        if not order_in.product_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="product_id or items is required",
            )
        raw_items = [{"product_id": order_in.product_id, "quantity": order_in.quantity}]

    customer_info = _public_customer_info(order_in)
    items_to_insert = []
    total_price = 0.0
    products_by_id = {}
    for raw_item in raw_items:
        product_id = raw_item.product_id if hasattr(raw_item, "product_id") else raw_item["product_id"]
        quantity = raw_item.quantity if hasattr(raw_item, "quantity") else raw_item["quantity"]
        if not ObjectId.is_valid(product_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product id")

        product = products_collection.find_one(
            {"_id": ObjectId(product_id), "shop_id": shop["_id"]}
        )
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        unit_price = float(product.get("price", 0))
        total_price += unit_price * quantity
        products_by_id[product["_id"]] = product
        items_to_insert.append({
            "product_id": product["_id"],
            "quantity": quantity,
        })

    now = now_utc()
    order = {
        "session_id": order_in.session_id,
        "shop_id": shop["_id"],
        "items": items_to_insert,
        "total_price": total_price,
        "status": "pending",
        "customer_info": customer_info,
        "created_at": now,
        "updated_at": now,
    }
    reserved_items: list[tuple[ObjectId, int]] = []
    try:
        for item in items_to_insert:
            reserved_product = _reserve_product_stock(
                {"_id": item["product_id"], "shop_id": shop["_id"]},
                item["quantity"],
                "Product is not available or out of stock",
            )
            reserved_items.append((reserved_product["_id"], item["quantity"]))
            products_by_id[reserved_product["_id"]] = reserved_product
        result = orders_collection.insert_one(order)
    except HTTPException:
        _restore_reserved_stock(reserved_items)
        raise
    except Exception:
        _restore_reserved_stock(reserved_items)
        raise

    return {
        "message": "Order created successfully.",
        "order_id": str(result.inserted_id),
        "status": "pending",
        "product": serialize_document(next(iter(products_by_id.values()))) if len(products_by_id) == 1 else None,
        "items": [
            {
                "product": serialize_document(products_by_id[item["product_id"]]),
                "quantity": item["quantity"],
            }
            for item in items_to_insert
        ],
        "quantity": sum(item["quantity"] for item in items_to_insert),
        "total_price": total_price,
        "delivery": _delivery_summary(shop, customer_info["city"]),
    }


@router.post("/public", status_code=status.HTTP_201_CREATED)
def create_public_order(shop_id: str, order_in: PublicOrderCreate) -> dict:
    """Create a customer order via the public chatbot endpoint."""
    return _create_public_order(shop_id, order_in)


@orders_router.post("", status_code=status.HTTP_201_CREATED)
def create_public_order_from_agent(order_in: PublicOrderCreate) -> dict:
    """Create a customer order from LangGraph using shop_id in the payload."""
    if not order_in.shop_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="shop_id is required",
        )
    return _create_public_order(order_in.shop_id, order_in)


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    shop_id: str,
    order_in: OrderCreate,
) -> dict:
    shop = _get_shop(shop_id)

    items_to_insert = []
    total_price = 0.0
    reserved_items: list[tuple[ObjectId, int]] = []

    try:
        for item in order_in.items:
            product = _get_shop_product(item.product_id, shop)
            unit_price = float(product.get("price", 0))
            total_price += unit_price * item.quantity
            reserved_product = _reserve_product_stock(
                {"_id": product["_id"], "shop_id": shop["_id"]},
                item.quantity,
                f"Product '{product.get('name')}' is not available or out of stock",
            )
            reserved_items.append((reserved_product["_id"], item.quantity))
            items_to_insert.append({
                "product_id": product["_id"],
                "quantity": item.quantity,
            })

        now = now_utc()
        order = {
            "session_id": order_in.session_id,
            "shop_id": shop["_id"],
            "items": items_to_insert,
            "total_price": total_price,
            "status": "pending",
            "customer_info": order_in.customer_info.model_dump(),
            "created_at": now,
            "updated_at": now,
        }
        result = orders_collection.insert_one(order)
    except HTTPException:
        _restore_reserved_stock(reserved_items)
        raise
    except Exception:
        _restore_reserved_stock(reserved_items)
        raise

    created = orders_collection.find_one({"_id": result.inserted_id})
    products_map = _fetch_products_map([created])
    return _serialize_order(created, products_map, shop.get("name", ""))


@router.get("", response_model=OrderListWithShopResponse)
def list_orders(
    shop_id: str,
) -> dict:
    shop = _get_shop(shop_id)
    orders = list(
        orders_collection.find({"shop_id": shop["_id"]}).sort("created_at", -1)
    )
    products_map = _fetch_products_map(orders)
    shop_name = shop.get("name", "")
    enriched = [_serialize_order(o, products_map, shop_name) for o in orders]
    return {"shop": serialize_document(shop), "orders": enriched}


@router.get("/session/{session_id}", response_model=OrderListWithShopResponse)
def list_orders_by_session(
    shop_id: str,
    session_id: str,
) -> dict:
    shop = _get_shop(shop_id)
    orders = list(
        orders_collection.find({"shop_id": shop["_id"], "session_id": session_id}).sort("created_at", -1)
    )
    products_map = _fetch_products_map(orders)
    shop_name = shop.get("name", "")
    enriched = [_serialize_order(o, products_map, shop_name) for o in orders]
    return {"shop": serialize_document(shop), "orders": enriched}


@router.get("/{order_id}", response_model=OrderDetailWithShopResponse)
def get_order(
    shop_id: str,
    order_id: str,
) -> dict:
    shop = _get_shop(shop_id)
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
) -> dict:
    shop = _get_shop(shop_id)
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


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    shop_id: str,
    order_id: str,
    body: OrderStatusUpdate,
) -> dict:
    shop = _get_shop(shop_id)
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object id")

    order = orders_collection.find_one({"_id": ObjectId(order_id), "shop_id": shop["_id"]})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    orders_collection.update_one(
        {"_id": order["_id"]},
        {"$set": {"status": body.status, "updated_at": now_utc()}},
    )

    if body.status == "confirmed" and order.get("status") != "confirmed":
        for item in order.get("items", []):
            products_collection.update_one(
                {"_id": item["product_id"]},
                {"$inc": {"stock": -item["quantity"]}},
            )

    updated = orders_collection.find_one({"_id": order["_id"]})
    products_map = _fetch_products_map([updated])
    return _serialize_order(updated, products_map, shop.get("name", ""))


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    shop_id: str,
    order_id: str,
) -> None:
    shop = _get_shop(shop_id)
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object id")

    result = orders_collection.delete_one({"_id": ObjectId(order_id), "shop_id": shop["_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")


@orders_router.get("/session/{session_id}", response_model=list[OrderResponse])
def get_orders_by_session(session_id: str) -> list:
    orders = list(
        orders_collection.find({"session_id": session_id}).sort("created_at", -1)
    )
    if not orders:
        return []

    shop_ids = list({o["shop_id"] for o in orders})
    shops_map = {s["_id"]: s for s in shops_collection.find({"_id": {"$in": shop_ids}})}
    products_map = _fetch_products_map(orders)

    return [
        _serialize_order(o, products_map, shops_map.get(o["shop_id"], {}).get("name", ""))
        for o in orders
    ]
