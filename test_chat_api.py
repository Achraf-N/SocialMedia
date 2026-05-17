"""Test the integrated chat API."""

import requests
import json

# API endpoint
API_URL = "http://localhost:8000/api/chat"

# Test data - using values from your backend shop
test_cases = [
    {
        "name": "Product List Query",
        "data": {
            "message": "What products do you have?",
            "session_id": "test_user_001",
            "shop_id": "6a09d431697b1d38b68a50ce"
        }
    },
    {
        "name": "Product Info Query",
        "data": {
            "message": "Tell me about string",
            "session_id": "test_user_001",
            "shop_id": "6a09d431697b1d38b68a50ce"
        }
    },
    {
        "name": "Price Query",
        "data": {
            "message": "How much is string?",
            "session_id": "test_user_001",
            "shop_id": "6a09d431697b1d38b68a50ce"
        }
    },
    {
        "name": "Greeting",
        "data": {
            "message": "Hello!",
            "session_id": "test_user_002",
            "shop_id": "6a09d431697b1d38b68a50ce"
        }
    },
    {
        "name": "Follow-up Question (Same Session)",
        "data": {
            "message": "What about delivery?",
            "session_id": "test_user_001",
            "shop_id": "6a09d431697b1d38b68a50ce"
        }
    }
]


def test_chat_api():
    """Test the chat API with various messages."""
    print("=" * 70)
    print("Testing Integrated Chat API")
    print("=" * 70)
    print(f"API: {API_URL}\n")
    
    for i, test_case in enumerate(test_cases, 1):
        name = test_case["name"]
        data = test_case["data"]
        
        print(f"\n[TEST {i}] {name}")
        print("-" * 70)
        print(f"Message:    {data['message']}")
        print(f"Session ID: {data['session_id']}")
        print(f"Shop ID:    {data['shop_id']}")
        
        try:
            # Send request
            response = requests.post(
                API_URL,
                json=data,
                timeout=30
            )
            
            # Check response
            if response.status_code == 200:
                result = response.json()
                print(f"\n✓ SUCCESS (Status: {response.status_code})")
                print(f"Response:       {result.get('response', 'N/A')}")
                print(f"Intent:         {result.get('intent', 'N/A')}")
                print(f"Active Product: {result.get('active_product', 'N/A')}")
                print(f"Confidence:     {result.get('confidence', 0):.2f}")
                print(f"Steps:          {len(result.get('steps', []))} steps executed")
                
                # Show first 2 steps
                steps = result.get("steps", [])
                if steps:
                    print("  Steps:")
                    for step in steps[:3]:
                        print(f"    - {step}")
                    if len(steps) > 3:
                        print(f"    ... and {len(steps) - 3} more")
            else:
                print(f"\n✗ ERROR (Status: {response.status_code})")
                print(f"Response: {response.text}")
        
        except requests.exceptions.ConnectionError:
            print(f"\n✗ CONNECTION ERROR")
            print(f"  Cannot connect to {API_URL}")
            print(f"  Make sure backend is running:")
            print(f"    cd backend")
            print(f"    uvicorn app.main:app --reload --port 8000")
            break
        except requests.exceptions.Timeout:
            print(f"\n✗ TIMEOUT")
            print(f"  Request took too long. Check if backend is responsive.")
        except Exception as e:
            print(f"\n✗ ERROR: {str(e)}")
    
    print("\n" + "=" * 70)
    print("Test complete!")
    print("=" * 70)


def test_health_endpoint():
    """Test the health endpoint."""
    print("\n" + "=" * 70)
    print("Testing Health Endpoints")
    print("=" * 70)
    
    endpoints = [
        ("Backend Health", "http://localhost:8000/health"),
        ("Chat Service Health", "http://localhost:8000/api/chat/health"),
    ]
    
    for name, url in endpoints:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"\n✓ {name}: {url}")
                print(f"  Response: {data}")
            else:
                print(f"\n✗ {name}: Status {response.status_code}")
        except Exception as e:
            print(f"\n✗ {name}: {str(e)}")
    
    print()


if __name__ == "__main__":
    # Test health endpoints first
    test_health_endpoint()
    
    # Test chat API
    test_chat_api()
