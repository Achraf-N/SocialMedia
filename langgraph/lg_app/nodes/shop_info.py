"""Node: Shop information agent."""

from lg_app.data.shop_data import SHOP_INFO
from lg_app.state import ChatState


def shop_info_agent(state: ChatState) -> ChatState:
    """Answer questions about the shop/store itself."""
    message = state["message"].lower()
    shop_info = state.get("shop_info") or SHOP_INFO
    shop_name = shop_info.get("name") or SHOP_INFO["name"]
    delivery = shop_info.get("delivery")
    payment = shop_info.get("payment")

    if "name" in message:
        state["response"] = f"The shop name is {shop_name}."
    elif "delivery" in message:
        state["response"] = delivery or "Delivery information is not available yet."
    elif "payment" in message or "pay" in message:
        state["response"] = payment or "Payment information is not available yet."
    else:
        state["response"] = f"{shop_name} offers the products listed in this shop catalog."

    state["steps"].append("Generated shop info response")
    return state
