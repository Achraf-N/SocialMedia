"""Intent requirement definitions for owner-agent workflows."""

from typing import Any


CREATE_PRODUCT_REQUIRED_FIELDS = ["name", "price"]

CREATE_PRODUCT_OPTIONAL_FIELDS = [
    "description",
    "available",
    "category",
    "stock",
    "delivery_time",
    "brand",
    "variants",
    "sizes",
    "colors",
    "images",
]

IMPORT_PRODUCT_REQUIRED_FIELDS = [
    "name",
    "price",
    "description",
    "category",
    "stock",
    "delivery_time",
    "brand",
]

INTENT_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "create_product": {
        "requires_shop": True,
        "required_fields": CREATE_PRODUCT_REQUIRED_FIELDS,
        "optional_fields": CREATE_PRODUCT_OPTIONAL_FIELDS,
        "ordered_fields": ["name", "price"],
        "requires_confirmation": False,
    },
    "import_products": {
        "requires_shop": True,
        "required_fields": IMPORT_PRODUCT_REQUIRED_FIELDS,
        "optional_fields": [],
        "ordered_fields": IMPORT_PRODUCT_REQUIRED_FIELDS,
        "requires_confirmation": False,
    },
}


def get_create_product_missing_fields(router_output: dict) -> list[str]:
    fields = router_output.get("fields") or {}
    missing = []

    if not fields.get("name"):
        missing.append("name")

    if fields.get("price") is None:
        missing.append("price")

    return missing


def get_create_product_question(missing_field: str, router_output: dict) -> str:
    fields = router_output.get("fields") or {}
    name = fields.get("name") or router_output.get("product_reference")

    if missing_field == "name":
        return "What is the product name?"

    if missing_field == "price":
        if name:
            return f"What price should I set for {name}?"
        return "What price should I set?"

    return "Please provide the missing product information."
