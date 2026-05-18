from typing import Any

from bson import ObjectId
from fastapi import Depends, HTTPException, Request, status

from app.core.database import owners_collection, shops_collection
from app.core.security import decode_access_token, extract_token_from_request
from app.views.serializers import serialize_document


def get_current_owner(request: Request) -> dict[str, Any]:
    token = extract_token_from_request(request)
    payload = decode_access_token(token)
    owner_id = payload.get("owner_id")

    if not owner_id or not ObjectId.is_valid(owner_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    owner = owners_collection.find_one({"_id": ObjectId(owner_id)})
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Owner no longer exists",
        )

    return owner


def get_current_shop(owner: dict[str, Any] = Depends(get_current_owner)) -> dict[str, Any]:
    shop = shops_collection.find_one({"owner_id": owner["_id"]})
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Create a shop before managing products or categories",
        )
    return shop


def get_shop_by_id(shop_id: str) -> dict[str, Any]:
    if not ObjectId.is_valid(shop_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object id")

    shop = shops_collection.find_one({"_id": ObjectId(shop_id)})
    if not shop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")

    return shop


def get_owned_shop(shop_id: str, owner: dict[str, Any]) -> dict[str, Any]:
    if not ObjectId.is_valid(shop_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object id")

    shop = shops_collection.find_one({"_id": ObjectId(shop_id), "owner_id": owner["_id"]})
    if not shop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")

    return shop


def serialized_current_owner(owner: dict[str, Any] = Depends(get_current_owner)) -> dict[str, Any]:
    return serialize_document(owner)
