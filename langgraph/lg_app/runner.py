"""Chat runner for the LangGraph workflow."""

from lg_app.state import ChatState
from lg_app.graph import get_graph


def run_chat(session_id: str, message: str, shop_id: str = "6a09d431697b1d38b68a50ce") -> dict:
    """
    Run a chat message through the LangGraph workflow.
    
    Args:
        session_id: User session identifier
        message: User message
        shop_id: Shop ID to fetch products from (defaults to demo shop)
        
    Returns:
        dict with keys: response, intent, active_product, confidence, steps
    """
    # Create compiled graph
    graph = get_graph()
    
    # Initialize state
    initial_state: ChatState = {
        "session_id": session_id,
        "shop_id": shop_id,
        "message": message,
        "intent": None,
        "product_query": None,
        "active_product": None,
        "current_product_id": None,
        "current_product": None,
        "current_product_name": None,
        "delivery_city": None,
        "delivery_address": None,
        "pending_order_json": None,
        "shop_info": None,
        "response": None,
        "steps": ["Received message"],
        "shop_data": [],
        "needs_human": False,
        "confidence": 0.0,
    }
    
    # Invoke graph
    final_state = graph.invoke(initial_state)
    
    # Return formatted result
    return {
        "response": final_state["response"],
        "intent": final_state["intent"],
        "active_product": final_state["active_product"],
        "current_product_id": final_state.get("current_product_id"),
        "current_product": final_state.get("current_product"),
        "current_product_name": final_state.get("current_product_name"),
        "delivery_city": final_state.get("delivery_city"),
        "delivery_address": final_state.get("delivery_address"),
        "confidence": final_state.get("confidence", 0.85),
        "steps": final_state["steps"],
    }


if __name__ == "__main__":
    """Test conversation with active_product session state."""
    
    print("\n" + "="*80)
    print("LangGraph Chatbot - Active Product State Management Test")
    print("="*80 + "\n")
    
    # Test 1: Product info flow
    print("[TEST 1] Start conversation and ask about Serum")
    result1 = run_chat("user1", "Tell me about Serum Vitamin C")
    print(f"Intent: {result1['intent']}")
    print(f"Active Product: {result1['active_product']}")
    print(f"Response: {result1['response'][:100]}...")
    assert result1["active_product"] == "Serum Vitamin C", "Should set Serum as active product"
    print("✓ PASS\n")
    
    # Test 2: Follow-up with "this product"
    print("[TEST 2] Follow-up: 'What is the price of this product?'")
    result2 = run_chat("user1", "What is the price of this product?")
    print(f"Intent: {result2['intent']}")
    print(f"Active Product: {result2['active_product']}")
    print(f"Response: {result2['response'][:100]}...")
    assert result2["active_product"] == "Serum Vitamin C", "Should keep Serum as active product"
    assert result2["intent"] == "price_question", "Should detect price question"
    print("✓ PASS\n")
    
    # Test 3: Switch to different product
    print("[TEST 3] Switch product: 'What about Hair Oil?'")
    result3 = run_chat("user1", "What about Hair Oil?")
    print(f"Intent: {result3['intent']}")
    print(f"Active Product: {result3['active_product']}")
    print(f"Response: {result3['response'][:100]}...")
    assert result3["active_product"] == "Hair Oil", "Should switch to Hair Oil"
    print("✓ PASS\n")
    
    # Test 4: Follow-up with "it"
    print("[TEST 4] Follow-up: 'How much is it?'")
    result4 = run_chat("user1", "How much is it?")
    print(f"Intent: {result4['intent']}")
    print(f"Active Product: {result4['active_product']}")
    print(f"Response: {result4['response'][:100]}...")
    assert result4["active_product"] == "Hair Oil", "Should keep Hair Oil as active product"
    assert result4["intent"] == "price_question", "Should detect price question"
    print("✓ PASS\n")
    
    # Test 5: Delivery question
    print("[TEST 5] Delivery question (general)")
    result5 = run_chat("user1", "How long is delivery?")
    print(f"Intent: {result5['intent']}")
    print(f"Active Product: {result5['active_product']}")
    print(f"Response: {result5['response'][:100]}...")
    assert result5["intent"] == "delivery_question", "Should detect delivery question"
    print("✓ PASS\n")
    
    # Test 6: New user session
    print("[TEST 6] New user session")
    result6 = run_chat("user2", "What products do you have?")
    print(f"Intent: {result6['intent']}")
    print(f"Active Product: {result6['active_product']}")
    print(f"Response: {result6['response'][:100]}...")
    assert result6["intent"] == "product_list", "Should detect product list"
    assert result6["active_product"] is None, "New user should have no active product"
    print("✓ PASS\n")
    
    # Test 7: Session isolation
    print("[TEST 7] User2 selects Face Cream")
    result7 = run_chat("user2", "Tell me about Face Cream")
    print(f"Intent: {result7['intent']}")
    print(f"Active Product: {result7['active_product']}")
    print(f"Response: {result7['response'][:100]}...")
    assert result7["active_product"] == "Face Cream", "User2 should have Face Cream"
    
    # Verify User1 still has Hair Oil
    result7b = run_chat("user1", "What is this?")
    print(f"\nUser1 context: {result7b['active_product']}")
    assert result7b["active_product"] == "Hair Oil", "User1 should still have Hair Oil"
    print("✓ PASS - Sessions isolated\n")
    
    # Test 8: Greeting without changing context
    print("[TEST 8] Greeting (should not change active_product)")
    result8 = run_chat("user2", "Hi there")
    print(f"Intent: {result8['intent']}")
    print(f"Active Product: {result8['active_product']}")
    assert result8["active_product"] == "Face Cream", "Active product should stay Face Cream"
    print("✓ PASS\n")
    
    print("="*80)
    print("ALL TESTS PASSED! ✓")
    print("="*80)
    print("\nSummary:")
    print("- Active product persists across messages in same session")
    print("- Active product updates when user mentions new product")
    print("- Router correctly uses active_product context")
    print("- Sessions are isolated between users")
    print("- Confidence scores included in responses")
    
    print("=" * 80)
    print("LangGraph Chatbot - Test Conversation")
    print("=" * 80)
    
    test_cases = [
        ("user1", "hello"),
        ("user1", "What services do you offer?"),
        ("user1", "Tell me about Serum Vitamin C"),
        ("user1", "What is the price of this product?"),
        ("user1", "What about Hair Oil?"),
        ("user1", "How much?"),
        ("user1", "How long is delivery?"),
        ("user1", "thank you"),
    ]
    
    for session_id, message in test_cases:
        print(f"\n[User] {message}")
        
        result = run_chat(session_id, message)
        
        print(f"[Bot] {result['response']}")
        print(f"[Intent] {result['intent']}")
        if result['active_product']:
            print(f"[Active Product] {result['active_product']}")
        
        print(f"[Steps]")
        for step in result['steps']:
            print(f"  - {step}")
        print("-" * 80)
