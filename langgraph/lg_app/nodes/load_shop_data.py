"""Node: Load shop data."""

from lg_app.state import ChatState
from lg_app.data.shop_data import SHOP_PRODUCTS


def load_shop_data(state: ChatState) -> ChatState:
    """Load shop product data into state."""
    state["shop_data"] = SHOP_PRODUCTS
    state["steps"].append("Loaded shop data")
    return state
