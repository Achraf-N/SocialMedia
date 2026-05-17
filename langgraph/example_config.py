"""Example configuration and usage guide for Ollama integration."""

# ============================================================================
# QUICK START
# ============================================================================
# 
# 1. Install Ollama: https://ollama.ai
# 2. Pull model: ollama pull qwen3:8b
# 3. Start server: ollama serve
# 4. Install dependencies: pip install -r requirements.txt
# 5. Run test: python -m app.runner
# 
# ============================================================================

# ============================================================================
# CUSTOM OLLAMA CONFIGURATION
# ============================================================================

from app.llm import OllamaLLM

# Example 1: Use different model
def use_mistral():
    llm = OllamaLLM(model="mistral")
    response = llm.generate("Hello!")
    print(response)

# Example 2: Use remote Ollama server
def use_remote_ollama():
    llm = OllamaLLM(
        model="qwen3:8b",
        base_url="http://192.168.1.100:11434"  # Remote server
    )
    response = llm.generate("Tell me about beauty products")
    print(response)

# Example 3: Generate with custom temperature
def custom_temperature():
    llm = OllamaLLM()
    
    # High temperature = more creative
    creative = llm.generate(
        "Write a product description for luxury serum",
        temperature=0.9
    )
    
    # Low temperature = more consistent
    consistent = llm.generate(
        "What is the price of vitamin C serum?",
        temperature=0.3
    )
    
    print("Creative:", creative)
    print("Consistent:", consistent)

# ============================================================================
# CUSTOM PROMPT ENGINEERING
# ============================================================================

# Edit app/llm/prompts.py to customize:

CUSTOM_SYSTEM_PROMPTS = {
    "product_info": """You are a luxury beauty consultant with 10 years of experience.
Provide sophisticated, personalized product recommendations.
Focus on ingredients, benefits, and why this product suits them.
Always be enthusiastic about quality beauty products.""",
}

CUSTOM_PROMPT_TEMPLATES = {
    "product_info": """Product: {name} by {brand}
Price: {price} MAD
Availability: {available}

Description: {description}
Stock: {stock} units available
Delivery: {delivery_time}

Provide an expert, detailed recommendation about this luxury product.""",
}

# ============================================================================
# PERFORMANCE TUNING
# ============================================================================

PERFORMANCE_CONFIGS = {
    # Fast responses (trade-off: less accurate)
    "fast": {
        "temperature": 0.5,
        "max_tokens": 128,
    },
    
    # Balanced (recommended for most use cases)
    "balanced": {
        "temperature": 0.7,
        "max_tokens": 256,
    },
    
    # High quality (trade-off: slower responses)
    "high_quality": {
        "temperature": 0.6,
        "max_tokens": 512,
    },
    
    # Creative (for greeting, small talk)
    "creative": {
        "temperature": 0.85,
        "max_tokens": 256,
    },
}

# ============================================================================
# TESTING LLM OUTPUT
# ============================================================================

def test_ollama_connection():
    """Test if Ollama is running and responding."""
    from app.llm import get_llm
    
    try:
        llm = get_llm()
        response = llm.generate(
            "Say 'Ollama is working!' in one sentence.",
            temperature=0.5,
            max_tokens=50
        )
        print(f"✓ Ollama working: {response}")
        return True
    except ConnectionError as e:
        print(f"✗ Ollama not running: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_product_agent():
    """Test the product info agent with LLM."""
    from app.runner import run_chat
    
    print("\n=== Testing Product Info Agent ===")
    result = run_chat("test_user", "Tell me about Serum Vitamin C")
    print(f"Intent: {result['intent']}")
    print(f"Active Product: {result['active_product']}")
    print(f"Response: {result['response']}")
    print(f"Steps: {len(result['steps'])} steps")

def test_all_agents():
    """Test all agents with LLM."""
    from app.runner import run_chat
    
    conversations = [
        ("Test 1: Greeting", "hello"),
        ("Test 2: Product List", "what do you sell?"),
        ("Test 3: Product Info", "hair oil details"),
        ("Test 4: Price", "how much is it?"),
        ("Test 5: Delivery", "when will it arrive?"),
        ("Test 6: Payment", "can I pay with card?"),
        ("Test 7: Small Talk", "thanks a lot!"),
        ("Test 8: Unknown", "xyz abc 123"),
    ]
    
    print("\n=== Full Test Suite ===\n")
    
    for title, message in conversations:
        result = run_chat("user1", message)
        print(f"\n{title}")
        print(f"  User: {message}")
        print(f"  Bot: {result['response']}")
        print(f"  Intent: {result['intent']}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test-connection":
            test_ollama_connection()
        elif sys.argv[1] == "test-product":
            test_product_agent()
        elif sys.argv[1] == "test-all":
            test_all_agents()
        else:
            print("Usage:")
            print("  python example_config.py test-connection  # Test Ollama connection")
            print("  python example_config.py test-product     # Test product agent")
            print("  python example_config.py test-all         # Test all agents")
    else:
        print("Configuration and testing guide loaded.")
        print("Run with arguments: test-connection, test-product, test-all")
