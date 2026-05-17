"""Test backend API integration."""

import json
from app.api.backend_client import get_backend_client, set_backend_url


def test_backend_client():
    """Test connecting to backend API."""
    print("=" * 80)
    print("Testing Backend API Integration")
    print("=" * 80)
    
    # Configure backend URL (update with your actual URL)
    backend_url = "http://localhost:8000"
    set_backend_url(backend_url)
    
    print(f"\n✓ Backend URL set to: {backend_url}")
    
    # Get client
    client = get_backend_client()
    
    # Test: Fetch shop with products
    print("\n[TEST 1] Fetching shop with products...")
    shop_id = "6a09d431697b1d38b68a50ce"  # Replace with your actual shop_id
    
    try:
        data = client.get_shop_with_products(shop_id)
        
        if data["products"]:
            print(f"✓ Successfully fetched {len(data['products'])} products")
            
            # Print shop info
            shop = data["shop"]
            print(f"\n  Shop: {shop['name']}")
            print(f"  Delivery: {shop['delivery']}")
            print(f"  ID: {shop['id']}")
            
            # Print first 2 products
            print("\n  Products:")
            for i, product in enumerate(data["products"][:2]):
                print(f"    {i+1}. {product['name']} - {product['price']} MAD")
                print(f"       Available: {product['available']}, Stock: {product['stock']}")
        else:
            print("✗ No products found")
    except Exception as e:
        print(f"✗ Error: {e}")
        print("  Make sure:")
        print("  - Backend is running on http://localhost:8000")
        print("  - Shop ID is correct")
        print("  - Replace shop_id with your actual shop_id from backend")
    
    # Test: Search for product
    print("\n[TEST 2] Searching for product...")
    try:
        product = client.find_product_by_name(shop_id, "string")
        if product:
            print(f"✓ Found product: {product['name']}")
            print(f"  Price: {product['price']}")
            print(f"  Available: {product['available']}")
        else:
            print("✗ Product not found")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "=" * 80)
    print("Backend integration test complete!")
    print("=" * 80)


if __name__ == "__main__":
    test_backend_client()
