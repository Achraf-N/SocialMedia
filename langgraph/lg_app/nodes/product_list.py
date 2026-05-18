"""Node: Product list agent."""

from lg_app.state import ChatState


def _set_current_product(state: ChatState, product: dict) -> None:
    """Update product context when a catalog request selects one product."""
    product_name = product.get("name")
    if not product_name:
        return
    state["active_product"] = product_name
    state["current_product"] = product_name
    state["current_product_name"] = product_name
    state["current_product_id"] = product.get("id") or product.get("_id")


def product_list_agent(state: ChatState) -> ChatState:
    """Handle product list request deterministically."""

    message = state["message"].lower()
    products = state.get("shop_data", [])
    catalog_filter = state.get("catalog_filter")

    wants_available_only = any(
        phrase in message
        for phrase in [
            "available",
            "in stock",
            "stock",
            "disponible",
        ]
    )
    wants_other_products = any(
        phrase in message
        for phrase in [
            "other products",
            "other product",
            "all other products",
            "all other product",
        ]
    )

    if wants_available_only:
        selected_products = [p for p in products if p.get("available") is True]
    else:
        selected_products = products

    if catalog_filter:
        selected_products = [
            p
            for p in selected_products
            if p.get("brand") == catalog_filter or p.get("category") == catalog_filter
        ]

    if wants_other_products and state.get("active_product"):
        selected_products = [
            p for p in selected_products if p.get("name") != state["active_product"]
        ]

    if not selected_products:
        state["response"] = "I could not find matching products at the moment."
        state["last_catalog_products"] = []
        state["steps"].append("Generated product list response")
        return state

    state["last_catalog_products"] = [p.get("name") for p in selected_products if p.get("name")]

    wants_cheapest = any(
        phrase in message
        for phrase in [
            "cheapest",
            "lowest price",
            "least expensive",
            "low price",
            "budget",
        ]
    )
    wants_most_expensive = any(
        phrase in message
        for phrase in [
            "most expensive",
            "highest price",
            "premium",
            "expensive one",
        ]
    )
    wants_details = any(
        phrase in message
        for phrase in [
            "details",
            "detail",
            "information",
            "info",
            "services provided",
            "service provided",
        ]
    )
    wants_prices = any(
        phrase in message
        for phrase in [
            "price",
            "prices",
            "how much",
            "cost",
        ]
    )

    if wants_cheapest:
        product = min(selected_products, key=lambda p: p.get("price", 0))
        _set_current_product(state, product)
        state["response"] = (
            f"The cheapest product is {product['name']} at {product['price']} MAD."
        )
        state["steps"].append("Generated cheapest product response")
        return state

    if wants_most_expensive:
        product = max(selected_products, key=lambda p: p.get("price", 0))
        _set_current_product(state, product)
        state["response"] = (
            f"The most expensive product is {product['name']} at {product['price']} MAD."
        )
        state["steps"].append("Generated most expensive product response")
        return state

    if wants_prices:
        parts = [
            f"{product['name']}: {product.get('price')} MAD"
            for product in selected_products
        ]
        state["response"] = "Product prices: " + ", ".join(parts) + "."
        state["steps"].append(
            f"Generated product price list response with {len(selected_products)} products"
        )
        return state

    if wants_details:
        lines = []
        for product in selected_products:
            availability = "available" if product.get("available") else "unavailable"
            lines.append(
                f"{product['name']}: {product.get('description', 'No description available')} "
                f"Price: {product.get('price')} MAD. Stock: {product.get('stock', 0)}. "
                f"Status: {availability}."
            )
        state["response"] = " ".join(lines)
        if catalog_filter and len(selected_products) > 1:
            state["response"] += f" Which {catalog_filter} product do you mean?"
        state["steps"].append(
            f"Generated detailed product list response with {len(selected_products)} products"
        )
        return state

    product_names = [p["name"] for p in selected_products]

    if catalog_filter:
        state["response"] = (
            f"For {catalog_filter}, I found: "
            + ", ".join(product_names)
            + ". Which one would you like to check?"
        )
    elif wants_available_only:
        state["response"] = (
            "Available products are: "
            + ", ".join(product_names)
            + "."
        )
    else:
        state["response"] = (
            "Here are the products we currently have: "
            + ", ".join(product_names)
            + "."
        )

    state["steps"].append(
        f"Generated product list response with {len(selected_products)} products"
    )

    return state
