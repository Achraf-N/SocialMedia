"""LangGraph workflow graph."""

from langgraph.graph import StateGraph, END

from lg_app.state import ChatState
from lg_app.nodes.load_shop_data import load_shop_data
from lg_app.nodes.load_session_state import load_session_state
from lg_app.nodes.router import intent_router
from lg_app.nodes.state_manager import update_active_product
from lg_app.nodes.product_list import product_list_agent
from lg_app.nodes.shop_info import shop_info_agent
from lg_app.nodes.product_info import product_info_agent
from lg_app.nodes.price import price_agent
from lg_app.nodes.delivery import delivery_agent
from lg_app.nodes.payment import payment_agent
from lg_app.nodes.order import order_agent
from lg_app.nodes.greeting import greeting_agent
from lg_app.nodes.small_talk import small_talk_agent
from lg_app.nodes.unknown import unknown_agent
from lg_app.nodes.human_needed import human_needed_agent
from lg_app.nodes.save_session_state import save_session_state_node


def route_by_intent(state: ChatState) -> str:
    """Route to appropriate agent based on detected intent."""
    intent_to_node = {
        "product_list": "product_list_agent",
        "shop_info_question": "shop_info_agent",
        "product_info_question": "product_info_agent",
        "availability_question": "product_info_agent",
        "order_intent": "order_agent",
        "order_creation": "order_agent",
        "price_question": "price_agent",
        "delivery_question": "delivery_agent",
        "payment_question": "payment_agent",
        "greeting": "greeting_agent",
        "small_talk": "small_talk_agent",
        "complaint": "human_needed_agent",
        "human_needed": "human_needed_agent",
        "unknown": "unknown_agent",
    }
    
    return intent_to_node.get(state["intent"], "unknown_agent")


def get_graph():
    """Build and return the compiled LangGraph workflow."""
    graph = StateGraph(ChatState)
    
    # Add all nodes
    graph.add_node("load_shop_data", load_shop_data)
    graph.add_node("load_session_state", load_session_state)
    graph.add_node("intent_router", intent_router)
    graph.add_node("update_active_product", update_active_product)
    
    graph.add_node("product_list_agent", product_list_agent)
    graph.add_node("shop_info_agent", shop_info_agent)
    graph.add_node("product_info_agent", product_info_agent)
    graph.add_node("price_agent", price_agent)
    graph.add_node("delivery_agent", delivery_agent)
    graph.add_node("payment_agent", payment_agent)
    graph.add_node("order_agent", order_agent)
    graph.add_node("greeting_agent", greeting_agent)
    graph.add_node("small_talk_agent", small_talk_agent)
    graph.add_node("unknown_agent", unknown_agent)
    graph.add_node("human_needed_agent", human_needed_agent)
    
    graph.add_node("save_session_state", save_session_state_node)
    
    # Set entry point
    graph.set_entry_point("load_shop_data")
    
    # Add edges
    graph.add_edge("load_shop_data", "load_session_state")
    graph.add_edge("load_session_state", "intent_router")
    graph.add_edge("intent_router", "update_active_product")
    
    # Conditional routing based on intent
    graph.add_conditional_edges(
        "update_active_product",
        route_by_intent,
        {
            "product_list_agent": "product_list_agent",
            "shop_info_agent": "shop_info_agent",
            "product_info_agent": "product_info_agent",
            "price_agent": "price_agent",
            "delivery_agent": "delivery_agent",
            "payment_agent": "payment_agent",
            "order_agent": "order_agent",
            "greeting_agent": "greeting_agent",
            "small_talk_agent": "small_talk_agent",
            "human_needed_agent": "human_needed_agent",
            "unknown_agent": "unknown_agent",
        }
    )
    
    # All agent nodes lead to save state
    agent_nodes = [
        "product_list_agent", "shop_info_agent", "product_info_agent", "price_agent",
        "delivery_agent", "payment_agent", "order_agent", "greeting_agent",
        "small_talk_agent", "unknown_agent", "human_needed_agent"
    ]
    for agent in agent_nodes:
        graph.add_edge(agent, "save_session_state")
    
    # Save state leads to end
    graph.add_edge("save_session_state", END)
    
    return graph.compile()
def build_graph():
    """Compatibility wrapper for backend bridge."""
    return get_graph()
