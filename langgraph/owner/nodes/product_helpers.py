"""Shared product-management helpers for owner nodes."""

from __future__ import annotations

from typing import Any

from owner import product_service
from owner.nodes import require_shop
from owner.owner_state import OwnerChatState


def router_payload(state: OwnerChatState) -> dict[str, Any]:
    return state.get("router_output") or state.get("extracted_data", {}).get("owner_router") or {}


def product_id(product: dict[str, Any]) -> str:
    return str(product.get("id") or product.get("_id") or product.get("name"))


def product_name(product: dict[str, Any]) -> str:
    return str(product.get("name") or "this product")


def format_money(price: Any, currency: str | None = None) -> str:
    if price is None:
        return "n/a"
    number = float(price)
    text = str(int(number)) if number.is_integer() else str(number)
    return f"{text} {currency or 'DH'}".strip()


def resolve_single_product(state: OwnerChatState) -> dict[str, Any] | None:
    if not require_shop(state):
        return None

    payload = router_payload(state)
    direct_product_id = payload.get("product_id")
    if direct_product_id:
        result = product_service.get_product(state["selected_shop_id"], str(direct_product_id))
        product = result.get("product") if isinstance(result, dict) and not result.get("ok") is False else None
        if product:
            state["last_product"] = {
                "id": product_id(product),
                "name": product_name(product),
                "price": product.get("price"),
                "stock": product.get("stock"),
            }
            return product
        state["response"] = "I could not find that product."
        state["needs_clarification"] = True
        state["steps"].append("Product id unresolved")
        return None

    reference = payload.get("product_reference")
    ordinal_product = resolve_ordinal_product(state, reference)
    if ordinal_product:
        state["last_product"] = {
            "id": product_id(ordinal_product),
            "name": product_name(ordinal_product),
            "price": ordinal_product.get("price"),
            "stock": ordinal_product.get("stock"),
        }
        return ordinal_product

    resolution = product_service.resolve_product_match(state["selected_shop_id"], reference)
    status = resolution["status"]
    if status == "single":
        product = resolution["product"]
        state["last_product"] = {
            "id": product_id(product),
            "name": product_name(product),
            "price": product.get("price"),
            "stock": product.get("stock"),
        }
        return product
    if status == "missing":
        state["response"] = "Which product should I update?"
    elif status == "none":
        state["response"] = f"I could not find a product matching {reference}."
    else:
        names = [product_name(product) for product in resolution.get("products", [])]
        state["response"] = "I found multiple matching products. Please choose one: " + ", ".join(names) + "."
    state["needs_clarification"] = True
    state["steps"].append("Product match unresolved")
    return None


def resolve_ordinal_product(state: OwnerChatState, reference: str | None) -> dict[str, Any] | None:
    if not reference:
        return None

    normalized = " ".join(str(reference).lower().split())
    ordinal_map = {
        "first": 0,
        "1st": 0,
        "one": 0,
        "second": 1,
        "2nd": 1,
        "two": 1,
        "third": 2,
        "3rd": 2,
        "three": 2,
        "last": -1,
        "latest": -1,
    }
    index = None
    for word, candidate in ordinal_map.items():
        if normalized in {word, f"{word} product", f"{word} products"} or normalized.startswith(f"{word} "):
            index = candidate
            break
    if index is None:
        return None

    products = state.get("last_products") or []
    if not products:
        return None
    if index < 0:
        return products[index]
    if index < len(products):
        return products[index]
    return None


def set_pending_confirmation(
    state: OwnerChatState,
    intent: str,
    product: dict[str, Any],
    payload: dict[str, Any],
    message: str,
) -> None:
    state["pending_confirmation"] = {
        "intent": intent,
        "shop_id": state.get("selected_shop_id"),
        "product_id": product_id(product),
        "product_name": product_name(product),
        "product_reference": product_name(product),
        "payload": payload,
    }
    state["response"] = message
    state["needs_clarification"] = True


def pop_matching_confirmation(state: OwnerChatState, intent: str) -> dict[str, Any] | None:
    payload = router_payload(state)
    pending = state.get("pending_confirmation") or {}
    if payload.get("action") == "confirm" and pending.get("intent") == intent:
        state["pending_confirmation"] = {}
        return pending
    return None
