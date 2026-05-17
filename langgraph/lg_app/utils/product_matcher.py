"""Product matching utility."""

import re
from typing import Optional


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


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
    msg_normalized = _normalize(message)
    
    # First try exact product name match
    for product in products:
        product_name = product.get("name", "")
        product_name_normalized = _normalize(product_name)
        if product_name_normalized and product_name_normalized in msg_normalized:
            return product
    
    message_tokens = set(msg_normalized.split())

    # Then try dynamic partial token matching from real product names.
    best_match = None
    best_score = 0.0
    for product in products:
        product_name = product.get("name", "")
        product_tokens = set(_normalize(product_name).split())
        if not product_tokens:
            continue

        matched_tokens = message_tokens.intersection(product_tokens)
        score = len(matched_tokens) / len(product_tokens)
        if score > best_score:
            best_match = product
            best_score = score

    if best_match and best_score >= 0.5:
        return best_match
    
    return None
