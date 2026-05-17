"""Node: Product list agent."""

from lg_app.state import ChatState


def product_list_agent(state: ChatState) -> ChatState:
    """Handle product list request deterministically."""

    message = state["message"].lower()
    products = state.get("shop_data", [])

    wants_available_only = any(
        phrase in message
        for phrase in [
            "available",
            "in stock",
            "stock",
            "disponible",
        ]
    )

    if wants_available_only:
        selected_products = [p for p in products if p.get("available") is True]
    else:
        selected_products = products

    if not selected_products:
        state["response"] = "I could not find matching products at the moment."
        state["steps"].append("Generated product list response")
        return state

    product_names = [p["name"] for p in selected_products]

    if wants_available_only:
        state["response"] = (
            "Available products include: "
            + ", ".join(product_names)
            + "."
        )
    else:
        state["response"] = (
            "We currently offer: "
            + ", ".join(product_names)
            + "."
        )

    state["steps"].append(
        f"Generated product list response with {len(selected_products)} products"
    )

    return state