"""Product matching utility."""

from typing import Optional


def find_product(message: str, products: list[dict]) -> Optional[dict]:
    """
    Find a product mentioned in the message.
    
    Matches:
    - Exact product names (case-insensitive)
    - Partial names and keywords:
      - "serum" → Serum Vitamin C
      - "vitamin c" → Serum Vitamin C
      - "hair oil" → Hair Oil
      - "oil" → Hair Oil
      - "cream" → Face Cream
    
    Args:
        message: User message
        products: List of product dictionaries
        
    Returns:
        Product dict if found, None otherwise
    """
    msg_lower = message.lower()
    
    # First try exact product name match
    for product in products:
        product_name_lower = product["name"].lower()
        if product_name_lower in msg_lower:
            return product
    
    # Then try partial matches with keywords
    keywords = {
        "serum": "Serum Vitamin C",
        "vitamin c": "Serum Vitamin C",
        "hair oil": "Hair Oil",
        "oil": "Hair Oil",
        "cream": "Face Cream",
    }
    
    for keyword, product_name in keywords.items():
        if keyword in msg_lower:
            for product in products:
                if product["name"] == product_name:
                    return product
    
    return None
