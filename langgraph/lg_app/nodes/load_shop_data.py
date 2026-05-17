"""Node: Load shop data from backend API or mock fallback."""

import os
import requests
from lg_app.state import ChatState
from lg_app.data.shop_data import SHOP_PRODUCTS

# Get backend URL from environment or use localhost
BACKEND_BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def load_shop_data(state: ChatState) -> ChatState:
    """Load shop product data from backend MongoDB.
    
    Falls back to mock data if backend is unavailable.
    """
    try:
        shop_id = state.get("shop_id", "")
        if not shop_id:
            raise ValueError("shop_id not provided")
        
        # Try to fetch from backend API endpoint
        url = f"{BACKEND_BASE_URL}/api/shops/{shop_id}/products"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        # Handle both list and dict responses
        if isinstance(data, list):
            products = data
        else:
            products = data.get("products", [])
        
        if products:
            state["shop_data"] = products
            state["steps"].append(f"Loaded {len(products)} products from backend MongoDB")
        else:
            # Fallback to mock if no products found
            state["shop_data"] = SHOP_PRODUCTS
            state["steps"].append("No products found, using mock data")
            
    except Exception as e:
        # Fallback to mock data on any error
        state["shop_data"] = SHOP_PRODUCTS
        state["steps"].append(f"Backend error: {str(e)}. Using mock data.")
    
    return state
