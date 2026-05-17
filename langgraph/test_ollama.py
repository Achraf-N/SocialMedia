"""Test Ollama connection and qwen3:8b availability."""

import requests
import json

print("\n" + "="*80)
print("Ollama Connection Test")
print("="*80 + "\n")

# Test 1: Check Ollama service
print("[TEST 1] Checking Ollama service on http://localhost:11434...")
try:
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    print(f"✓ Ollama service is running")
    print(f"  Status code: {response.status_code}")
    
    models = response.json()
    print(f"\n  Available models:")
    if models.get("models"):
        for model in models["models"]:
            print(f"    - {model['name']}")
    else:
        print("    (No models listed)")
        
except requests.exceptions.ConnectionError:
    print("✗ FAILED: Cannot connect to Ollama")
    print("  Make sure Ollama is running on http://localhost:11434")
    print("  Start Ollama with: ollama serve")
    exit(1)
except Exception as e:
    print(f"✗ FAILED: {e}")
    exit(1)

# Test 2: Check if qwen3:8b is available
print("\n[TEST 2] Checking for qwen3:8b model...")
try:
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    models = response.json().get("models", [])
    
    qwen_found = any("qwen" in model["name"].lower() for model in models)
    
    if qwen_found:
        print("✓ qwen model found!")
        for model in models:
            if "qwen" in model["name"].lower():
                print(f"  - {model['name']}")
    else:
        print("⚠ No qwen model found")
        print("  Available models:", [m["name"] for m in models])
        print("\n  To install qwen3:8b:")
        print("    ollama pull qwen3:8b")
        
except Exception as e:
    print(f"✗ FAILED: {e}")
    exit(1)

# Test 3: Test model generation
print("\n[TEST 3] Testing qwen3:8b model generation...")
try:
    payload = {
        "model": "qwen3:8b",
        "prompt": "Hello, what is 2+2?",
        "stream": False,
        "temperature": 0.7,
    }
    
    response = requests.post(
        "http://localhost:11434/api/generate",
        json=payload,
        timeout=60
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Model generation successful!")
        print(f"\n  Prompt: 'Hello, what is 2+2?'")
        print(f"  Response: {result.get('response', 'N/A')[:100]}...")
        print(f"\n  Generation stats:")
        print(f"    - Load time: {result.get('load_duration', 0) / 1e9:.2f}s")
        print(f"    - Generate time: {result.get('eval_duration', 0) / 1e9:.2f}s")
        print(f"    - Total tokens: {result.get('eval_count', 0)}")
    else:
        print(f"✗ FAILED: Status code {response.status_code}")
        print(f"  Response: {response.text}")
        
except requests.exceptions.Timeout:
    print("✗ FAILED: Model generation timed out (60s)")
    print("  Model may be slow or not available")
except requests.exceptions.ConnectionError:
    print("✗ FAILED: Cannot connect to Ollama API")
except Exception as e:
    print(f"✗ FAILED: {e}")

print("\n" + "="*80)
print("Ollama Connection Test Complete")
print("="*80 + "\n")
