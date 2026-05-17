from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.core.database import categories_collection
from app.core.dependencies import get_current_owner, get_owned_shop
from app.models.category_model import CategoryCreate, CategoryResponse, CategoryUpdate
from app.models.common import now_utc
from app.views.serializers import serialize_document, serialize_documents

router = APIRouter(prefix="/shops/{shop_id}/categories", tags=["categories"])


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    shop_id: str,
    category_in: CategoryCreate,
    owner: dict = Depends(get_current_owner),
) -> dict:
    shop = get_owned_shop(shop_id, owner)
    now = now_utc()
    category = {
        "owner_id": owner["_id"],
        "shop_id": shop["_id"],
        "name": category_in.name,
        "created_at": now,
        "updated_at": now,
    }

    try:
        result = categories_collection.insert_one(category)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category already exists for this shop",
        ) from exc

    return serialize_document(categories_collection.find_one({"_id": result.inserted_id}))


@router.get("", response_model=list[CategoryResponse])
def list_categories(
    shop_id: str,
    owner: dict = Depends(get_current_owner),
) -> list[dict]:
    shop = get_owned_shop(shop_id, owner)
    categories = list(
        categories_collection.find({"owner_id": owner["_id"], "shop_id": shop["_id"]}).sort(
            "name", 1
        )
    )
    return serialize_documents(categories)


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    shop_id: str,
    category_id: str,
    owner: dict = Depends(get_current_owner),
) -> dict:
    shop = get_owned_shop(shop_id, owner)
    if not ObjectId.is_valid(category_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object id")

    category = categories_collection.find_one(
        {"_id": ObjectId(category_id), "owner_id": owner["_id"], "shop_id": shop["_id"]}
    )
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    return serialize_document(category)


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    shop_id: str,
    category_id: str,
    category_in: CategoryUpdate,
    owner: dict = Depends(get_current_owner),
) -> dict:
    shop = get_owned_shop(shop_id, owner)
    if not ObjectId.is_valid(category_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object id")

    try:
        result = categories_collection.update_one(
            {"_id": ObjectId(category_id), "owner_id": owner["_id"], "shop_id": shop["_id"]},
            {"$set": {"name": category_in.name, "updated_at": now_utc()}},
        )
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category already exists for this shop",
        ) from exc

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    return serialize_document(categories_collection.find_one({"_id": ObjectId(category_id)}))


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    shop_id: str,
    category_id: str,
    owner: dict = Depends(get_current_owner),
) -> None:
    shop = get_owned_shop(shop_id, owner)
    if not ObjectId.is_valid(category_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object id")

    result = categories_collection.delete_one(
        {"_id": ObjectId(category_id), "owner_id": owner["_id"], "shop_id": shop["_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
