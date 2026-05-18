from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import (
    categories_collection,
    orders_collection,
    products_collection,
    shops_collection,
)
from app.core.dependencies import get_current_owner
from app.models.common import now_utc, oid
from app.core.dependencies import get_shop_by_id
from app.models.shop_model import ShopCreate, ShopPublicResponse, ShopResponse, ShopUpdate
from app.views.serializers import serialize_document, serialize_documents, serialize_shop_public

router = APIRouter(prefix="/shops", tags=["shops"])


@router.get("/public/debug", status_code=status.HTTP_200_OK)
def debug_all_shops() -> dict:
    """
    DEBUG ONLY: List all shops in database (for troubleshooting).
    """
    try:
        shops = list(shops_collection.find({}))
        return {
            "total_shops": len(shops),
            "shops": [
                {
                    "id": str(s.get("_id")),
                    "name": s.get("name"),
                    "delivery": s.get("delivery"),
                    "owner_id": str(s.get("owner_id"))
                }
                for s in shops
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{shop_id}/products/public", status_code=status.HTTP_200_OK)
def get_shop_products_public(shop_id: str) -> dict:
    """
    Public endpoint for chat bot to fetch shop details and products.
    No authentication required.
    """
    try:
        if not ObjectId.is_valid(shop_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object id")
        
        shop_obj_id = ObjectId(shop_id)
        shop = shops_collection.find_one({"_id": shop_obj_id})
        
        if not shop:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")
        
        # Get products for this shop
        products = list(products_collection.find({"shop_id": shop_obj_id}))
        
        return {
            "shop": serialize_document(shop),
            "products": serialize_documents(products)
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("", response_model=ShopResponse, status_code=status.HTTP_201_CREATED)
def create_shop(
    shop_in: ShopCreate,
    owner: dict = Depends(get_current_owner),
) -> dict:
    now = now_utc()
    shop = {
        "owner_id": owner["_id"],
        "name": shop_in.name,
        "delivery": shop_in.delivery,
        "created_at": now,
        "updated_at": now,
    }
    result = shops_collection.insert_one(shop)
    created_shop = shops_collection.find_one({"_id": result.inserted_id})
    return serialize_document(created_shop)


@router.get("", response_model=list[ShopPublicResponse])
def list_shops() -> list[dict]:
    """List all shops (public)."""
    shops = list(shops_collection.find({}).sort("created_at", -1))
    return [serialize_shop_public(shop) for shop in shops]


@router.get("/me", response_model=list[ShopResponse])
def get_my_shops(owner: dict = Depends(get_current_owner)) -> list[dict]:
    shops = list(shops_collection.find({"owner_id": owner["_id"]}).sort("created_at", -1))
    return serialize_documents(shops)


@router.get("/{shop_id}", response_model=ShopPublicResponse)
def get_shop(shop_id: str) -> dict:
    """Get a shop by id (public)."""
    shop = get_shop_by_id(shop_id)
    return serialize_shop_public(shop)


@router.patch("/{shop_id}", response_model=ShopResponse)
def update_shop(
    shop_id: str,
    shop_in: ShopUpdate,
    owner: dict = Depends(get_current_owner),
) -> dict:
    try:
        shop_object_id = oid(shop_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    update_data = shop_in.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    update_data["updated_at"] = now_utc()
    result = shops_collection.update_one(
        {"_id": shop_object_id, "owner_id": owner["_id"]},
        {"$set": update_data},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")

    return serialize_document(shops_collection.find_one({"_id": shop_object_id}))


@router.delete("/{shop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shop(shop_id: str, owner: dict = Depends(get_current_owner)) -> None:
    if not ObjectId.is_valid(shop_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object id")

    result = shops_collection.delete_one({"_id": ObjectId(shop_id), "owner_id": owner["_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")

    products_collection.delete_many({"owner_id": owner["_id"], "shop_id": ObjectId(shop_id)})
    categories_collection.delete_many({"owner_id": owner["_id"], "shop_id": ObjectId(shop_id)})
    orders_collection.delete_many({"shop_id": ObjectId(shop_id)})
