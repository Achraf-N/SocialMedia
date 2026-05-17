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
from app.views.serializers import serialize_document, serialize_documents

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


@router.post("/public", status_code=status.HTTP_201_CREATED)
def create_public_order(shop_id: str, order_in: PublicOrderCreate) -> dict:
    """Create a customer order for a public shop without owner authentication."""
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product is not available")

    now = now_utc()
    order = {
        "customer_name": order_in.customer_name,
        "delivery_address": order_in.address,
        "city": order_in.city,
        "phone_number": order_in.customer_phone,
        "payment_method": order_in.payment_method,
        "quantity": order_in.quantity,
        "product_id": product["_id"],
        "owner_id": shop.get("owner_id"),
        "shop_id": shop["_id"],
        "status": "pending",
        "delivered": False,
        "created_at": now,
        "updated_at": now,
    }
    result = orders_collection.insert_one(order)
    total_price = product.get("price", 0) * order_in.quantity

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
    product = _get_owned_product(order_in.product_id, owner, shop)
    now = now_utc()
    order = {
        **order_in.model_dump(),
        "product_id": product["_id"],
        "owner_id": owner["_id"],
        "shop_id": shop["_id"],
        "created_at": now,
        "updated_at": now,
    }
    result = orders_collection.insert_one(order)
    return serialize_document(orders_collection.find_one({"_id": result.inserted_id}))


@router.get("", response_model=OrderListWithShopResponse)
def list_orders(
    shop_id: str,
    owner: dict = Depends(get_current_owner),
) -> dict:
    shop = get_owned_shop(shop_id, owner)
    orders = list(
        orders_collection.find({"owner_id": owner["_id"], "shop_id": shop["_id"]}).sort(
            "created_at", -1
        )
    )
    return {"shop": serialize_document(shop), "orders": serialize_documents(orders)}


@router.get("/{order_id}", response_model=OrderDetailWithShopResponse)
def get_order(
    shop_id: str,
    order_id: str,
    owner: dict = Depends(get_current_owner),
) -> dict:
    shop = get_owned_shop(shop_id, owner)
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object id")

    order = orders_collection.find_one(
        {"_id": ObjectId(order_id), "owner_id": owner["_id"], "shop_id": shop["_id"]}
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return {"shop": serialize_document(shop), "order": serialize_document(order)}


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

    if "product_id" in update_data:
        product = _get_owned_product(update_data["product_id"], owner, shop)
        update_data["product_id"] = product["_id"]

    update_data["updated_at"] = now_utc()
    result = orders_collection.update_one(
        {"_id": ObjectId(order_id), "owner_id": owner["_id"], "shop_id": shop["_id"]},
        {"$set": update_data},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return serialize_document(orders_collection.find_one({"_id": ObjectId(order_id)}))


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    shop_id: str,
    order_id: str,
    owner: dict = Depends(get_current_owner),
) -> None:
    shop = get_owned_shop(shop_id, owner)
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object id")

    result = orders_collection.delete_one(
        {"_id": ObjectId(order_id), "owner_id": owner["_id"], "shop_id": shop["_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
