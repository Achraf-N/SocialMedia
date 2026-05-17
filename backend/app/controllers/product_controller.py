from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.database import categories_collection, products_collection, shops_collection
from app.core.dependencies import get_current_owner, get_owned_shop
from app.core.storage import upload_product_image
from app.models.common import now_utc
from app.models.product_model import (
    ProductCreate,
    ProductDetailWithShopResponse,
    ProductListWithShopResponse,
    ProductResponse,
    ProductUpdate,
)
from app.views.serializers import serialize_document, serialize_documents

router = APIRouter(prefix="/shops/{shop_id}/products", tags=["products"])


def _upsert_category(owner_id: ObjectId, shop_id: ObjectId, category_name: str) -> None:
    now = now_utc()
    categories_collection.update_one(
        {"owner_id": owner_id, "shop_id": shop_id, "name": category_name},
        {
            "$setOnInsert": {
                "owner_id": owner_id,
                "shop_id": shop_id,
                "name": category_name,
                "created_at": now,
            },
            "$set": {"updated_at": now},
        },
        upsert=True,
    )


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    shop_id: str,
    product_in: ProductCreate,
) -> dict:
    """Create a product in a shop (public endpoint for testing)."""
    if not ObjectId.is_valid(shop_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid shop id")
    
    shop_obj_id = ObjectId(shop_id)
    # Verify shop exists
    shop = shops_collection.find_one({"_id": shop_obj_id})
    if not shop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")
    
    now = now_utc()
    _upsert_category(shop.get("owner_id"), shop_obj_id, product_in.category)
    product = {
        **product_in.model_dump(),
        "owner_id": shop.get("owner_id"),
        "shop_id": shop_obj_id,
        "created_at": now,
        "updated_at": now,
    }
    result = products_collection.insert_one(product)
    return serialize_document(products_collection.find_one({"_id": result.inserted_id}))



@router.get("", response_model=ProductListWithShopResponse)
def list_products(shop_id: str) -> dict:
    """List all products for a shop with public shop details."""
    
    if not ObjectId.is_valid(shop_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid shop id"
        )

    shop_obj_id = ObjectId(shop_id)

    # Verify shop exists
    shop = shops_collection.find_one({"_id": shop_obj_id})
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found"
        )

    products = list(
        products_collection.find({"shop_id": shop_obj_id}).sort("created_at", -1)
    )

    return {
        "shop": serialize_document(shop),
        "products": serialize_documents(products),
    }


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(shop_id: str, product_id: str) -> dict:
    """Get a specific product (public endpoint)."""

    if not ObjectId.is_valid(shop_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid shop id"
        )

    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product id"
        )

    product = products_collection.find_one(
        {
            "_id": ObjectId(product_id),
            "shop_id": ObjectId(shop_id),
        }
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return serialize_document(product)

@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    shop_id: str,
    product_id: str,
    product_in: ProductUpdate,
    owner: dict = Depends(get_current_owner),
) -> dict:
    shop = get_owned_shop(shop_id, owner)
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object id")

    update_data = product_in.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    if "category" in update_data:
        _upsert_category(owner["_id"], shop["_id"], update_data["category"])

    update_data["updated_at"] = now_utc()
    result = products_collection.update_one(
        {"_id": ObjectId(product_id), "owner_id": owner["_id"], "shop_id": shop["_id"]},
        {"$set": update_data},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    return serialize_document(products_collection.find_one({"_id": ObjectId(product_id)}))


@router.patch("/{product_id}/image", response_model=ProductResponse)
def update_product_image(
    shop_id: str,
    product_id: str,
    image: UploadFile = File(...),
    owner: dict = Depends(get_current_owner),
) -> dict:
    shop = get_owned_shop(shop_id, owner)
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object id")

    product = products_collection.find_one(
        {"_id": ObjectId(product_id), "owner_id": owner["_id"], "shop_id": shop["_id"]}
    )
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    public_url = upload_product_image(
        file=image,
        owner_id=str(owner["_id"]),
        shop_id=str(shop["_id"]),
        product_id=str(product["_id"]),
    )
    products_collection.update_one(
        {"_id": product["_id"], "owner_id": owner["_id"], "shop_id": shop["_id"]},
        {"$set": {"image": public_url, "updated_at": now_utc()}},
    )

    return serialize_document(products_collection.find_one({"_id": product["_id"]}))


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    shop_id: str,
    product_id: str,
    owner: dict = Depends(get_current_owner),
) -> None:
    shop = get_owned_shop(shop_id, owner)
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object id")

    result = products_collection.delete_one(
        {"_id": ObjectId(product_id), "owner_id": owner["_id"], "shop_id": shop["_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
