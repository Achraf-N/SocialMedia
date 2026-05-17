"""Helper to load LangGraph modules into backend."""

import sys
from pathlib import Path

# Structure:
# he/
# ├── backend/
# │   └── app/
# └── langgraph/
#     └── app/

# backend/app/langgraph_bridge.py
CURRENT_FILE = Path(__file__).resolve()

BACKEND_DIR = CURRENT_FILE.parent.parent      # backend/
PROJECT_ROOT = BACKEND_DIR.parent             # he/
LANGGRAPH_DIR = PROJECT_ROOT / "langgraph"

print(f"📍 LangGraph path: {LANGGRAPH_DIR}")
print(f"   Exists: {LANGGRAPH_DIR.exists()}")

if LANGGRAPH_DIR.exists():
    sys.path.insert(0, str(LANGGRAPH_DIR))
    print("   ✓ Added to sys.path")
else:
    print(f"   ✗ MISSING! Expected at: {LANGGRAPH_DIR}")

try:
    print("\n📦 Importing from langgraph...")

    print("  1. Importing build_graph...")
    from lg_app.graph import build_graph
    print("     ✓ build_graph imported")

    print("  2. Importing ChatState...")
    from lg_app.state import ChatState
    print("     ✓ ChatState imported")

    print("  3. Importing backend_client...")
    
    print("     ✓ backend_client imported")

    print("\n✓ All LangGraph modules imported successfully!\n")

except ImportError as e:
    print(f"\n✗ Import Error: {e}")
    print(f"  Module search path: {sys.path[:5]}")

    import traceback
    traceback.print_exc()
    raise

except Exception as e:
    print(f"\n✗ Unexpected error: {type(e).__name__}: {e}")

    import traceback
    traceback.print_exc()
    raise


__all__ = [
    "build_graph",
    "ChatState",
    "get_backend_client",
    "set_backend_url",
]