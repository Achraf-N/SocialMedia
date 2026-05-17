"""Test chat API integration with MongoDB backend."""

import requests
import json
from time import sleep

BASE_URL = "http://localhost:8000"
SHOP_ID = "6a09d431697b1d38b68a50ce"  # Default shop from config

def test_chat_api():
    """Test the chat API endpoint with backend data."""
    
    print("\n" + "="*80)
    print("Testing Chat API Integration with MongoDB")
    print("="*80 + "\n")
    
    # Test 1: Check if app is running
    print("[1] Checking if backend is running...")
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✓ Backend health: {health.json()}")
    except Exception as e:
        print(f"✗ Backend not responding: {e}")
        return False
    
    # Test 2: Check if chat service is initialized
    print("\n[2] Checking if chat service is ready...")
    try:
        chat_health = requests.get(f"{BASE_URL}/api/chat/health", timeout=5)
        print(f"✓ Chat health: {chat_health.json()}")
        if not chat_health.json().get("graph_loaded"):
            print("✗ WARNING: Graph not loaded")
    except Exception as e:
        print(f"✗ Chat health check failed: {e}")
    
    # Test 3: Fetch shop products from backend API
    print(f"\n[3] Fetching products from backend API for shop {SHOP_ID}...")
    try:
        products_response = requests.get(
            f"{BASE_URL}/api/shops/{SHOP_ID}/products",
            timeout=5
        )
        products_data = products_response.json()
        products = products_data.get("products", [])
        print(f"✓ Fetched {len(products)} products from MongoDB:")
        for p in products:
            print(f"  - {p.get('name')}: ${p.get('price')} ({p.get('category')})")
    except Exception as e:
        print(f"✗ Failed to fetch products: {e}")
        return False
    
    # Test 4: Send chat message using real backend data
    print(f"\n[4] Sending chat message to use real backend data...")
    try:
        chat_request = {
            "message": "What products do you have?",
            "session_id": "test_user_001",
            "shop_id": SHOP_ID
        }
        
        chat_response = requests.post(
            f"{BASE_URL}/api/chat",
            json=chat_request,
            timeout=10
        )
        
        if chat_response.status_code == 200:
            result = chat_response.json()
            print(f"✓ Chat response received:")
            print(f"  Response: {result.get('response')[:150]}...")
            print(f"  Intent: {result.get('intent')}")
            print(f"  Confidence: {result.get('confidence')}")
            print(f"  Steps taken: {len(result.get('steps', []))} steps")
            for step in result.get('steps', [])[:3]:
                print(f"    - {step}")
        else:
            print(f"✗ Chat returned status {chat_response.status_code}")
            print(f"  Response: {chat_response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Chat request failed: {e}")
        return False
    
    # Test 5: Test product info query
    print(f"\n[5] Testing product info query...")
    try:
        chat_request = {
            "message": "Tell me about the first product",
            "session_id": "test_user_001",
            "shop_id": SHOP_ID
        }
        
        chat_response = requests.post(
            f"{BASE_URL}/api/chat",
            json=chat_request,
            timeout=10
        )
        
        if chat_response.status_code == 200:
            result = chat_response.json()
            print(f"✓ Product info response:")
            print(f"  Intent: {result.get('intent')}")
            print(f"  Active Product: {result.get('active_product')}")
            print(f"  Response: {result.get('response')[:100]}...")
        else:
            print(f"✗ Request failed: {chat_response.status_code}")
            
    except Exception as e:
        print(f"✗ Request failed: {e}")
    
    print("\n" + "="*80)
    print("✓ Integration test complete!")
    print("="*80 + "\n")
    return True

if __name__ == "__main__":
    test_chat_api()
