"""Owner LangGraph workflow."""

from langgraph.graph import END, StateGraph

from owner.owner_state import OwnerChatState
from owner.nodes.add_product import add_product_node
from owner.nodes.greeting import greeting_node
from owner.nodes.help import help_node
from owner.nodes.list_orders import list_orders_node
from owner.nodes.list_products import list_products_node
from owner.nodes.list_shops import list_shops_node
from owner.nodes.load_owner_context import load_owner_context
from owner.nodes.owner_router import owner_router
from owner.nodes.save_owner_state import save_owner_state_node
from owner.nodes.select_shop import select_shop_node
from owner.nodes.shop_summary import shop_summary_node
from owner.nodes.unknown import unknown_node
from owner.nodes.update_order_status import update_order_status_node
from owner.nodes.update_price import update_price_node
from owner.nodes.update_product import update_product_node
from owner.nodes.update_stock import update_stock_node


def route_by_owner_intent(state: OwnerChatState) -> str:
    mapping = {
        "greeting": "greeting",
        "list_shops": "list_shops",
        "select_shop": "select_shop",
        "shop_summary": "shop_summary",
        "list_products": "list_products",
        "add_product": "add_product",
        "update_product": "update_product",
        "update_stock": "update_stock",
        "update_price": "update_price",
        "list_orders": "list_orders",
        "update_order_status": "update_order_status",
        "help": "help",
        "unknown": "unknown",
    }
    return mapping.get(state.get("intent"), "unknown")


def get_owner_graph():
    graph = StateGraph(OwnerChatState)
    graph.add_node("load_owner_context", load_owner_context)
    graph.add_node("owner_router", owner_router)
    graph.add_node("greeting", greeting_node)
    graph.add_node("list_shops", list_shops_node)
    graph.add_node("select_shop", select_shop_node)
    graph.add_node("shop_summary", shop_summary_node)
    graph.add_node("list_products", list_products_node)
    graph.add_node("add_product", add_product_node)
    graph.add_node("update_product", update_product_node)
    graph.add_node("update_stock", update_stock_node)
    graph.add_node("update_price", update_price_node)
    graph.add_node("list_orders", list_orders_node)
    graph.add_node("update_order_status", update_order_status_node)
    graph.add_node("help", help_node)
    graph.add_node("unknown", unknown_node)
    graph.add_node("save_owner_state", save_owner_state_node)

    graph.set_entry_point("load_owner_context")
    graph.add_edge("load_owner_context", "owner_router")
    graph.add_conditional_edges(
        "owner_router",
        route_by_owner_intent,
        {
            "greeting": "greeting",
            "list_shops": "list_shops",
            "select_shop": "select_shop",
            "shop_summary": "shop_summary",
            "list_products": "list_products",
            "add_product": "add_product",
            "update_product": "update_product",
            "update_stock": "update_stock",
            "update_price": "update_price",
            "list_orders": "list_orders",
            "update_order_status": "update_order_status",
            "help": "help",
            "unknown": "unknown",
        },
    )
    for node in [
        "greeting",
        "list_shops",
        "select_shop",
        "shop_summary",
        "list_products",
        "add_product",
        "update_product",
        "update_stock",
        "update_price",
        "list_orders",
        "update_order_status",
        "help",
        "unknown",
    ]:
        graph.add_edge(node, "save_owner_state")
    graph.add_edge("save_owner_state", END)
    return graph.compile()
