"""Deterministic product service helpers for the owner agent."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from owner import owner_backend_client


def create_product(shop_id: str, data: dict[str, Any]) -> dict[str, Any]:
    product_data = _clean_product_fields(data)
    return owner_backend_client.create_product(shop_id, product_data)


def update_product(shop_id: str, product_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    update_data = _clean_product_fields(fields, include_create_only=False)
    return owner_backend_client.update_product(shop_id, product_id, update_data)


def delete_product(shop_id: str, product_id: str) -> dict[str, Any]:
    return owner_backend_client.delete_product(shop_id, product_id)


def get_product(shop_id: str, product_id: str) -> dict[str, Any]:
    return owner_backend_client.get_product(shop_id, product_id)


def search_products(shop_id: str, query: str | None) -> list[dict[str, Any]]:
    products = list_products(shop_id)
    if not query:
        return products

    normalized_query = _normalize(query)
    scored = []
    for product in products:
        name = str(product.get("name") or "")
        normalized_name = _normalize(name)
        if not normalized_name:
            continue
        score = SequenceMatcher(None, normalized_query, normalized_name).ratio()
        if normalized_query in normalized_name or normalized_name in normalized_query:
            score = max(score, 0.92)
        query_terms = set(normalized_query.split())
        name_terms = set(normalized_name.split())
        if query_terms and query_terms.issubset(name_terms):
            score = max(score, 0.9)
        elif query_terms & name_terms:
            score = max(score, 0.55)
        if score >= 0.55:
            scored.append((score, product))

    scored.sort(key=lambda item: (item[0], str(item[1].get("name") or "")), reverse=True)
    return [product for _, product in scored]


def list_products(shop_id: str) -> list[dict[str, Any]]:
    data = owner_backend_client.get_shop_products(shop_id)
    if isinstance(data, dict) and data.get("ok") is False:
        return []
    if isinstance(data, dict) and isinstance(data.get("products"), list):
        return data["products"]
    if isinstance(data, list):
        return data
    return []


def update_stock(shop_id: str, product_id: str, operation: str, quantity: int) -> dict[str, Any]:
    operation_map = {"increment": "increase", "decrement": "decrease"}
    backend_operation = operation_map.get(operation, operation)
    return owner_backend_client.update_product_stock(
        shop_id,
        product_id,
        {"operation": backend_operation, "quantity": int(quantity)},
    )


def update_price(shop_id: str, product_id: str, price: float, currency: str | None = None) -> dict[str, Any]:
    result = owner_backend_client.update_product_price(shop_id, product_id, float(price))
    if currency and not _is_error(result):
        product = result.get("product") if isinstance(result, dict) else None
        if isinstance(product, dict):
            product["currency"] = currency
    return result


def mark_unavailable(shop_id: str, product_id: str) -> dict[str, Any]:
    return owner_backend_client.update_product(shop_id, product_id, {"available": False})


def resolve_product_match(shop_id: str, product_reference: str | None) -> dict[str, Any]:
    if not product_reference:
        return {"status": "missing", "products": []}

    matches = search_products(shop_id, product_reference)
    if not matches:
        return {"status": "none", "products": []}

    exact = [product for product in matches if _normalize(product.get("name")) == _normalize(product_reference)]
    if len(exact) == 1:
        return {"status": "single", "product": exact[0], "products": exact}
    if len(exact) > 1:
        return {"status": "ambiguous", "products": exact}

    best_name = _normalize(matches[0].get("name"))
    best_score = SequenceMatcher(None, _normalize(product_reference), best_name).ratio()
    if len(matches) == 1 or best_score >= 0.86:
        return {"status": "single", "product": matches[0], "products": matches}
    return {"status": "ambiguous", "products": matches[:5]}


def _clean_product_fields(data: dict[str, Any], include_create_only: bool = True) -> dict[str, Any]:
    allowed = {
        "name",
        "description",
        "price",
        "stock",
        "category",
        "available",
        "images",
        "image",
        "brand",
        "delivery_time",
        "variants",
    }
    cleaned = {key: value for key, value in data.items() if key in allowed and value not in (None, "", [], {})}
    variants = list(cleaned.get("variants") or [])
    for field in ("sizes", "colors"):
        for value in data.get(field) or []:
            if value and value not in variants:
                variants.append(value)
    if variants:
        cleaned["variants"] = variants
    if include_create_only and "available" not in cleaned:
        cleaned["available"] = True
    images = cleaned.pop("images", None)
    if images and not cleaned.get("image"):
        cleaned["image"] = images[0]
    return cleaned


def _normalize(value: Any) -> str:
    return " ".join(str(value or "").lower().strip().split())


def _is_error(data: Any) -> bool:
    return isinstance(data, dict) and data.get("ok") is False
