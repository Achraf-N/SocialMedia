"""Owner LangGraph workflow."""

from langgraph.graph import END, StateGraph

from owner.owner_state import OwnerChatState
from owner.nodes.add_product import create_product_node
from owner.nodes.delete_product import delete_product_node
from owner.nodes.get_product import get_product_node
from owner.nodes.greeting import greeting_node
from owner.nodes.help import help_node
from owner.nodes.list_orders import list_orders_node
from owner.nodes.list_products import list_products_node
from owner.nodes.list_shops import list_shops_node
from owner.nodes.load_owner_context import load_owner_context
from owner.nodes.mark_unavailable import mark_unavailable_node
from owner.nodes.owner_router import owner_router
from owner.nodes.save_owner_state import save_owner_state_node
from owner.nodes.resolve_pending_field import resolve_pending_field_node
from owner.nodes.select_shop import select_shop_node
from owner.nodes.shop_summary import shop_summary_node
from owner.nodes.unknown import unknown_node
from owner.nodes.update_order_status import update_order_status_node
from owner.nodes.update_price import update_price_node
from owner.nodes.update_product import update_product_node
from owner.nodes.update_stock import update_stock_node
from owner.nodes import SHOP_REQUIRED_INTENTS


def route_by_owner_intent(state: OwnerChatState) -> str:
    mapping = {
        "greeting": "greeting",
        "list_shops": "list_shops",
        "select_shop": "select_shop",
        "shop_summary": "shop_summary",
        "list_products": "list_products",
        "create_product": "create_product",
        "add_product": "add_product",
        "delete_product": "delete_product",
        "get_product": "get_product",
        "update_product": "update_product",
        "update_stock": "update_stock",
        "update_price": "update_price",
        "mark_unavailable": "mark_unavailable",
        "list_orders": "list_orders",
        "update_order_status": "update_order_status",
        "help": "help",
        "unknown": "unknown",
    }
    return mapping.get(state.get("intent"), "unknown")


def route_after_select_shop(state: OwnerChatState) -> str:
    if state.get("response_prefix") and state.get("intent") in SHOP_REQUIRED_INTENTS:
        return route_by_owner_intent(state)
    return "save_owner_state"


def route_after_pending_field(state: OwnerChatState) -> str:
    if state.get("intent") == "update_product" and (state.get("router_output") or {}).get("product_id"):
        return "update_product"
    return "owner_router"


def get_owner_graph():
    graph = StateGraph(OwnerChatState)
    graph.add_node("load_owner_context", load_owner_context)
    graph.add_node("resolve_pending_field", resolve_pending_field_node)
    graph.add_node("owner_router", owner_router)
    graph.add_node("greeting", greeting_node)
    graph.add_node("list_shops", list_shops_node)
    graph.add_node("select_shop", select_shop_node)
    graph.add_node("shop_summary", shop_summary_node)
    graph.add_node("list_products", list_products_node)
    graph.add_node("create_product", create_product_node)
    graph.add_node("add_product", create_product_node)
    graph.add_node("delete_product", delete_product_node)
    graph.add_node("get_product", get_product_node)
    graph.add_node("update_product", update_product_node)
    graph.add_node("update_stock", update_stock_node)
    graph.add_node("update_price", update_price_node)
    graph.add_node("mark_unavailable", mark_unavailable_node)
    graph.add_node("list_orders", list_orders_node)
    graph.add_node("update_order_status", update_order_status_node)
    graph.add_node("help", help_node)
    graph.add_node("unknown", unknown_node)
    graph.add_node("save_owner_state", save_owner_state_node)

    graph.set_entry_point("load_owner_context")
    graph.add_edge("load_owner_context", "resolve_pending_field")
    graph.add_conditional_edges(
        "resolve_pending_field",
        route_after_pending_field,
        {
            "update_product": "update_product",
            "owner_router": "owner_router",
        },
    )
    graph.add_conditional_edges(
        "owner_router",
        route_by_owner_intent,
        {
            "greeting": "greeting",
            "list_shops": "list_shops",
            "select_shop": "select_shop",
            "shop_summary": "shop_summary",
            "list_products": "list_products",
            "create_product": "create_product",
            "add_product": "add_product",
            "delete_product": "delete_product",
            "get_product": "get_product",
            "update_product": "update_product",
            "update_stock": "update_stock",
            "update_price": "update_price",
            "mark_unavailable": "mark_unavailable",
            "list_orders": "list_orders",
            "update_order_status": "update_order_status",
            "help": "help",
            "unknown": "unknown",
        },
    )
    graph.add_conditional_edges(
        "select_shop",
        route_after_select_shop,
        {
            "shop_summary": "shop_summary",
            "list_products": "list_products",
            "create_product": "create_product",
            "delete_product": "delete_product",
            "get_product": "get_product",
            "update_product": "update_product",
            "update_stock": "update_stock",
            "update_price": "update_price",
            "mark_unavailable": "mark_unavailable",
            "list_orders": "list_orders",
            "update_order_status": "update_order_status",
            "save_owner_state": "save_owner_state",
        },
    )
    for node in [
        "greeting",
        "list_shops",
        "shop_summary",
        "list_products",
        "create_product",
        "add_product",
        "delete_product",
        "get_product",
        "update_product",
        "update_stock",
        "update_price",
        "mark_unavailable",
        "list_orders",
        "update_order_status",
        "help",
        "unknown",
    ]:
        graph.add_edge(node, "save_owner_state")
    graph.add_edge("save_owner_state", END)
    return graph.compile()
