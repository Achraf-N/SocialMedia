"""Populate MongoDB with test data for the chat API."""

from app.core.database import (
    owners_collection, shops_collection, products_collection, 
    categories_collection
)
from datetime import datetime
from bson import ObjectId

def populate_test_data():
    """Insert test owner, shop, categories, and products."""
    
    print("\n" + "="*80)
    print("Populating MongoDB with Test Data")
    print("="*80 + "\n")
    
    # Clear existing data
    print("[1] Clearing existing test data...")
    owners_collection.delete_many({})
    shops_collection.delete_many({})
    products_collection.delete_many({})
    categories_collection.delete_many({})
    print("✓ Collections cleared\n")
    
    # Create owner
    print("[2] Creating test owner...")
    owner = {
        "email": "shop_owner@example.com",
        "name": "Beauty Shop Owner",
        "created_at": datetime.utcnow()
    }
    owner_result = owners_collection.insert_one(owner)
    owner_id = owner_result.inserted_id
    print(f"✓ Owner created: {owner_id}\n")
    
    # Create shop
    print("[3] Creating test shop...")
    shop = {
        "owner_id": owner_id,
        "name": "Beauty Shop Casa",
        "delivery": "Casablanca 25 MAD, other cities 35 MAD, delivery in 24-72h",
        "payment": "Cash on delivery available",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    shop_result = shops_collection.insert_one(shop)
    shop_id = shop_result.inserted_id
    print(f"✓ Shop created: {shop_id}\n")
    
    # Create categories
    print("[4] Creating categories...")
    categories_data = [
        {
            "owner_id": owner_id,
            "shop_id": shop_id,
            "name": "Skin Care",
            "created_at": datetime.utcnow()
        },
        {
            "owner_id": owner_id,
            "shop_id": shop_id,
            "name": "Hair Care",
            "created_at": datetime.utcnow()
        }
    ]
    categories_result = categories_collection.insert_many(categories_data)
    print(f"✓ {len(categories_result.inserted_ids)} categories created\n")
    
    # Create products
    print("[5] Creating test products...")
    products_data = [
        {
            "owner_id": owner_id,
            "shop_id": shop_id,
            "name": "Serum Vitamin C",
            "price": 149,
            "description": "Brightening serum for dark spots",
            "available": True,
            "category": "Skin Care",
            "stock": 18,
            "delivery_time": "24-48h",
            "brand": "GlowSkin",
            "variants": ["30ml", "50ml"],
            "image": "https://example.com/images/serum-vitamin-c.jpg",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "owner_id": owner_id,
            "shop_id": shop_id,
            "name": "Hair Oil",
            "price": 99,
            "description": "Natural oil for dry hair",
            "available": True,
            "category": "Hair Care",
            "stock": 12,
            "delivery_time": "24-48h",
            "brand": "BeautyCare",
            "variants": ["100ml", "200ml"],
            "image": "https://example.com/images/hair-oil.jpg",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "owner_id": owner_id,
            "shop_id": shop_id,
            "name": "Face Cream",
            "price": 120,
            "description": "Hydrating face cream for daily use",
            "available": False,
            "category": "Skin Care",
            "stock": 0,
            "delivery_time": "3-5 days",
            "brand": "PureGlow",
            "variants": ["50ml"],
            "image": "https://example.com/images/face-cream.jpg",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    products_result = products_collection.insert_many(products_data)
    print(f"✓ {len(products_result.inserted_ids)} products created:")
    for product in products_data:
        print(f"  - {product['name']} (${product['price']})")
    
    print("\n" + "="*80)
    print("Test Data Summary")
    print("="*80)
    print(f"Owner ID: {owner_id}")
    print(f"Shop ID:  {shop_id}")
    print(f"Shop Name: {shop['name']}")
    print(f"Products: {len(products_result.inserted_ids)}")
    print(f"Categories: {len(categories_result.inserted_ids)}")
    print("\nUse this Shop ID in /api/chat requests:")
    print(f"  shop_id: '{str(shop_id)}'")
    print("="*80 + "\n")
    
    return str(shop_id)

if __name__ == "__main__":
    shop_id = populate_test_data()
