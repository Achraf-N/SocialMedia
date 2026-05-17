from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import categories_collection, products_collection, shops_collection
from app.core.dependencies import get_current_owner
from app.models.common import now_utc, oid
from app.models.shop_model import ShopCreate, ShopResponse, ShopUpdate
from app.views.serializers import serialize_document, serialize_documents

router = APIRouter(prefix="/shops", tags=["shops"])


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


@router.get("", response_model=list[ShopResponse])
def list_shops(owner: dict = Depends(get_current_owner)) -> list[dict]:
    shops = list(shops_collection.find({"owner_id": owner["_id"]}).sort("created_at", -1))
    return serialize_documents(shops)


@router.get("/me", response_model=list[ShopResponse])
def get_my_shops(owner: dict = Depends(get_current_owner)) -> list[dict]:
    shops = list(shops_collection.find({"owner_id": owner["_id"]}).sort("created_at", -1))
    return serialize_documents(shops)


@router.get("/{shop_id}", response_model=ShopResponse)
def get_shop(shop_id: str, owner: dict = Depends(get_current_owner)) -> dict:
    if not ObjectId.is_valid(shop_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object id")

    shop = shops_collection.find_one({"_id": ObjectId(shop_id), "owner_id": owner["_id"]})
    if not shop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")

    return serialize_document(shop)


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
