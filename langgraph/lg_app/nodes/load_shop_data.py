"""Node: Load shop data from backend API or mock fallback."""

import os
import requests
from lg_app.state import ChatState
from lg_app.data.shop_data import SHOP_INFO, SHOP_PRODUCTS

# Get backend URL from environment or use localhost
BACKEND_BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def _load_from_backend_db(shop_id: str) -> tuple[dict, list[dict]] | None:
    """Load shop/products directly when LangGraph runs inside the backend app."""
    try:
        from bson import ObjectId
        from app.core.database import products_collection, shops_collection
        from app.views.serializers import serialize_document, serialize_documents
    except Exception:
        return None

    if not ObjectId.is_valid(shop_id):
        return None

    shop_obj_id = ObjectId(shop_id)
    shop = shops_collection.find_one({"_id": shop_obj_id})
    if not shop:
        return None

    products = list(products_collection.find({"shop_id": shop_obj_id}).sort("created_at", -1))
    return serialize_document(shop), serialize_documents(products)


def load_shop_data(state: ChatState) -> ChatState:
    """Load shop product data from backend MongoDB.
    
    Falls back to mock data if backend is unavailable.
    """
    try:
        shop_id = state.get("shop_id", "")
        if not shop_id:
            raise ValueError("shop_id not provided")

        direct_data = _load_from_backend_db(shop_id)
        if direct_data:
            shop, products = direct_data
            state["shop_info"] = shop or SHOP_INFO
            state["shop_data"] = products
            state["steps"].append(f"Loaded {len(products)} products directly from backend MongoDB")
            return state
        
        # Try to fetch from backend API endpoint
        url = f"{BACKEND_BASE_URL}/api/shops/{shop_id}/products"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        # Handle both list and dict responses
        if isinstance(data, list):
            products = data
            state["shop_info"] = SHOP_INFO
        else:
            products = data.get("products", [])
            state["shop_info"] = data.get("shop") or SHOP_INFO
        
        if products:
            state["shop_data"] = products
            state["steps"].append(f"Loaded {len(products)} products from backend MongoDB")
        else:
            # Fallback to mock if no products found
            state["shop_data"] = SHOP_PRODUCTS
            state["shop_info"] = SHOP_INFO
            state["steps"].append("No products found, using mock data")
            
    except Exception as e:
        # Fallback to mock data on any error
        state["shop_data"] = SHOP_PRODUCTS
        state["shop_info"] = SHOP_INFO
        state["steps"].append(f"Backend error: {str(e)}. Using mock data.")
    
    return state
