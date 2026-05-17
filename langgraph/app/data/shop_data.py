"""Shop product and info data."""

SHOP_PRODUCTS = [
    {
        "name": "Serum Vitamin C",
        "price": 149,
        "description": "Brightening serum for dark spots",
        "available": True,
        "category": "Skin Care",
        "stock": 18,
        "delivery_time": "24-48h",
        "brand": "GlowSkin",
        "variants": ["30ml", "50ml"],
        "image": "https://example.com/images/serum-vitamin-c.jpg"
    },
    {
        "name": "Hair Oil",
        "price": 99,
        "description": "Natural oil for dry hair",
        "available": True,
        "category": "Hair Care",
        "stock": 12,
        "delivery_time": "24-48h",
        "brand": "BeautyCare",
        "variants": ["100ml", "200ml"],
        "image": "https://example.com/images/hair-oil.jpg"
    },
    {
        "name": "Face Cream",
        "price": 120,
        "description": "Hydrating face cream for daily use",
        "available": False,
        "category": "Skin Care",
        "stock": 0,
        "delivery_time": "3-5 days",
        "brand": "PureGlow",
        "variants": ["50ml"],
        "image": "https://example.com/images/face-cream.jpg"
    }
]

SHOP_INFO = {
    "name": "Beauty Shop Casa",
    "delivery": "Casablanca 25 MAD, other cities 35 MAD, delivery in 24-72h",
    "payment": "Cash on delivery is available. Other payment methods can be confirmed with the shop owner."
}
