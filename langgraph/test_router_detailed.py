"""Debug router detection - detailed."""

from app.utils.product_matcher import find_product
from app.data.shop_data import SHOP_PRODUCTS

msg = "What is the price of this product?"
msg_lower = msg.lower()

print(f"Message: '{msg}'")
print(f"Message (lowercase): '{msg_lower}'")
print()

# Check greeting
greeting_words = ["hello", "hi", "salam", "hey"]
greeting_match = any(word in msg_lower for word in greeting_words)
print(f"Greeting check: {greeting_match}")
for word in greeting_words:
    print(f"  '{word}' in message: {word in msg_lower}")
print()

# Check small talk
small_talk_words = ["thank you", "thanks", "ok", "okay", "bye", "good", "understood"]
small_talk_match = any(word in msg_lower for word in small_talk_words)
print(f"Small talk check: {small_talk_match}")
for word in small_talk_words:
    print(f"  '{word}' in message: {word in msg_lower}")
print()

# Check product list
product_list_phrases = ["products", "catalog", "what do you offer", "what services", "what do you sell", "available products", "what do you provide", "what can i buy"]
product_list_match = any(phrase in msg_lower for phrase in product_list_phrases)
print(f"Product list check: {product_list_match}")
for phrase in product_list_phrases:
    print(f"  '{phrase}' in message: {phrase in msg_lower}")
print()

# Check product info
product_info_words = ["details", "explain", "info", "available", "usage", "benefits", "ingredients"]
product = find_product(msg, SHOP_PRODUCTS)
product_info_match = any(word in msg_lower for word in product_info_words) or product
print(f"Product info check: {product_info_match}")
print(f"  Product found: {product}")
for word in product_info_words:
    print(f"  '{word}' in message: {word in msg_lower}")
print()

# Check price
price_words = ["price", "cost", "how much", "discount"]
price_match = any(word in msg_lower for word in price_words)
print(f"Price check: {price_match}")
for word in price_words:
    print(f"  '{word}' in message: {word in msg_lower}")
print()

# Check delivery
delivery_words = ["delivery", "shipping", "arrive", "cities", "how long"]
delivery_match = any(word in msg_lower for word in delivery_words)
print(f"Delivery check: {delivery_match}")
for word in delivery_words:
    print(f"  '{word}' in message: {word in msg_lower}")
print()

# Check payment
payment_words = ["payment", "pay", "cash", "card", "bank transfer"]
payment_match = any(word in msg_lower for word in payment_words)
print(f"Payment check: {payment_match}")
for word in payment_words:
    print(f"  '{word}' in message: {word in msg_lower}")
print()

# Check complaint
complaint_words = ["refund", "problem", "angry", "late", "bad", "issue"]
complaint_match = any(word in msg_lower for word in complaint_words)
print(f"Complaint check: {complaint_match}")
print()

# Check human needed
human_needed_words = ["support", "order not arrived"]
human_needed_match = any(word in msg_lower for word in human_needed_words)
print(f"Human needed check: {human_needed_match}")
