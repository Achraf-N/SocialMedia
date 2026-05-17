from typing import Any

from bson import ObjectId


def serialize_document(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if document is None:
        return None

    serialized = dict(document)
    serialized["id"] = str(serialized.pop("_id"))

    for key in ("owner_id", "shop_id", "product_id"):
        if key in serialized and isinstance(serialized[key], ObjectId):
            serialized[key] = str(serialized[key])

    return serialized


def serialize_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [serialize_document(document) for document in documents if document is not None]


def serialize_shop_public(document: dict[str, Any] | None) -> dict[str, Any] | None:
    serialized = serialize_document(document)
    if serialized is None:
        return None
    serialized.pop("owner_id", None)
    return serialized


def serialize_product(document: dict[str, Any] | None) -> dict[str, Any] | None:
    serialized = serialize_document(document)
    if serialized is None:
        return None
    serialized["image"] = serialized.get("image") or ""
    serialized.pop("owner_id", None)
    serialized.pop("shop_id", None)
    return serialized


def serialize_products(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [serialize_product(document) for document in documents if document is not None]
