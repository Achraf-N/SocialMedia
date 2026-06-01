import io

import pandas as pd
from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import ValidationError

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
from app.views.serializers import serialize_product, serialize_products, serialize_shop_public

_COLUMN_ALIASES: dict[str, list[str]] = {
    "name":          ["name", "product_name", "nom", "produit", "titre", "title"],
    "price":         ["price", "prix", "cost", "coût", "tarif"],
    "description":   ["description", "desc", "details", "détails"],
    "category":      ["category", "catégorie", "categorie", "type"],
    "stock":         ["stock", "quantity", "quantité", "qte", "qty"],
    "delivery_time": ["delivery_time", "delivery", "délai", "delai", "livraison"],
    "brand":         ["brand", "marque", "fabricant", "manufacturer"],
    "available":     ["available", "disponible", "dispo", "in_stock"],
    "variants":      ["variants", "variantes", "options", "sizes", "colors"],
}

_REQUIRED_FIELDS = {"name", "price", "description", "category", "stock", "delivery_time", "brand"}


def _normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    alias_to_field = {alias: field for field, aliases in _COLUMN_ALIASES.items() for alias in aliases}
    df.columns = [alias_to_field.get(c.lower().strip(), c.lower().strip()) for c in df.columns]
    return df


def _parse_file(content: bytes, content_type: str, filename: str) -> pd.DataFrame:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "csv" or "csv" in content_type:
        return pd.read_csv(io.BytesIO(content), dtype=str)
    if ext in ("xlsx", "xls") or "spreadsheet" in content_type or "excel" in content_type:
        return pd.read_excel(io.BytesIO(content), dtype=str)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type — use CSV or XLSX")

router = APIRouter(prefix="/shops/{shop_id}/products", tags=["products"])


def _upsert_category(owner_id: ObjectId, shop_id: ObjectId, category_name: str) -> None:
    if not category_name:
        return
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
        "image": "",
        "owner_id": shop.get("owner_id"),
        "shop_id": shop_obj_id,
        "created_at": now,
        "updated_at": now,
    }
    result = products_collection.insert_one(product)
    return serialize_product(products_collection.find_one({"_id": result.inserted_id}))



@router.post("/import")
def import_products(
    shop_id: str,
    file: UploadFile = File(...),
) -> dict:
    """Bulk-import products from a CSV or XLSX file."""
    if not ObjectId.is_valid(shop_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid shop id")

    shop_obj_id = ObjectId(shop_id)
    shop = shops_collection.find_one({"_id": shop_obj_id})
    if not shop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")

    content = file.file.read()
    df = _parse_file(content, file.content_type or "", file.filename or "")
    df = _normalize_headers(df)

    missing = _REQUIRED_FIELDS - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing required columns: {', '.join(sorted(missing))}",
        )

    owner_id = shop.get("owner_id")
    now = now_utc()
    to_insert: list[dict] = []
    failed: list[dict] = []

    for idx, row in df.iterrows():
        row_num = int(idx) + 2  # 1-based, +1 for header
        try:
            raw = row.to_dict()
            # Parse variants from pipe-separated string
            variants_raw = raw.get("variants", "")
            if pd.isna(variants_raw) or str(variants_raw).strip() == "":
                variants = []
            else:
                variants = [v.strip() for v in str(variants_raw).split("|") if v.strip()]

            available_raw = raw.get("available", "true")
            if pd.isna(available_raw):
                available = True
            else:
                available = str(available_raw).strip().lower() not in ("false", "0", "no", "non")

            product_in = ProductCreate(
                name=str(raw["name"]).strip(),
                price=float(raw["price"]),
                description=str(raw["description"]).strip(),
                category=str(raw["category"]).strip(),
                stock=int(float(raw["stock"])),
                delivery_time=str(raw["delivery_time"]).strip(),
                brand=str(raw["brand"]).strip(),
                available=available,
                variants=variants,
            )
        except (ValidationError, ValueError, KeyError) as exc:
            failed.append({"row": row_num, "error": str(exc)})
            continue

        _upsert_category(owner_id, shop_obj_id, product_in.category)
        to_insert.append({
            **product_in.model_dump(),
            "image": "",
            "owner_id": owner_id,
            "shop_id": shop_obj_id,
            "created_at": now,
            "updated_at": now,
        })

    inserted = 0
    if to_insert:
        result = products_collection.insert_many(to_insert)
        inserted = len(result.inserted_ids)

    return {"inserted": inserted, "failed": failed}


@router.get("", response_model=ProductListWithShopResponse)
def list_products(shop_id: str) -> dict:
    """List all products for a shop (public endpoint)."""
    
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
    return {"shop": serialize_shop_public(shop), "products": serialize_products(products)}


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    return serialize_product(product)

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

    return serialize_product(products_collection.find_one({"_id": ObjectId(product_id)}))


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

    return serialize_product(products_collection.find_one({"_id": product["_id"]}))


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
