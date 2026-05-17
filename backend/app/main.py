from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from app.controllers import (
    auth_controller,
    category_controller,
    order_controller,
    product_controller,
    shop_controller,
)
from app.core.config import settings
from app.core.database import create_indexes


# Import LangGraph for chat
try:
    from app.langgraph_bridge import build_graph, ChatState
    print("✓ LangGraph bridge imported successfully")
except Exception as e:
    print(f"✗ ERROR: Failed to import LangGraph bridge: {e}")
    import traceback
    traceback.print_exc()
    build_graph = None
    ChatState = None

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    try:
        create_indexes()
        print("✓ Database indexes created")
    except Exception as e:
        print(f"⚠ Warning: Could not create database indexes: {e}")
        print("  Make sure MongoDB is running on localhost:27017")
        print("  Chat endpoint will not work until MongoDB is available")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# ============================================================================
# Chat Endpoint (LangGraph Integration)
# ============================================================================

class ChatRequest(BaseModel):
    """Chat request from frontend."""
    message: str
    session_id: str
    shop_id: Optional[str] = "6a09d431697b1d38b68a50ce"  # Default shop ID


class ChatResponse(BaseModel):
    """Chat response to frontend."""
    response: str
    intent: Optional[str] = None
    active_product: Optional[str] = None
    session_id: str
    confidence: float
    steps: List[str] = []


# Initialize LangGraph graph
graph = None
if build_graph is not None:
    try:
        print("\n📊 Initializing LangGraph...")
        graph = build_graph()
        print("✓ LangGraph graph initialized successfully\n")
    except Exception as e:
        print(f"\n✗ ERROR: Failed to initialize LangGraph graph:")
        print(f"  {type(e).__name__}: {str(e)}\n")
        import traceback
        traceback.print_exc()
else:
    print("\n✗ ERROR: build_graph function is not available")
    print("  LangGraph bridge import failed\n")


@app.post("/api/chat", response_model=ChatResponse, tags=["chat"])
def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint - LangGraph integration.
    
    Frontend sends:
    {
        "message": "What products do you have?",
        "session_id": "user123",
        "shop_id": "6a09d431697b1d38b68a50ce"  (optional, has default)
    }
    
    Returns:
    {
        "response": "Here are our products...",
        "intent": "product_list",
        "active_product": null,
        "session_id": "user123",
        "confidence": 0.95,
        "steps": [...]
    }
    """
    try:
        # Validate dependencies
        if graph is None or ChatState is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chat service not initialized. Check server logs."
            )
        
        # Create initial state
        state = ChatState(
            session_id=request.session_id,
            shop_id=request.shop_id,
            message=request.message,
            intent=None,
            product_query=None,
            active_product=None,
            response=None,
            steps=[],
            shop_data=[],
            needs_human=False,
            confidence=0.0
        )
        
        # Run LangGraph workflow
        result = graph.invoke(state)
        
        # Return response to frontend
        return ChatResponse(
            response=result.get("response", "I couldn't process your request"),
            intent=result.get("intent"),
            active_product=result.get("active_product"),
            session_id=request.session_id,
            confidence=result.get("confidence", 0.0),
            steps=result.get("steps", [])
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing error: {str(e)}"
        )


@app.get("/api/chat/health", tags=["chat"])
def chat_health() -> dict:
    """Check if chat service is ready."""
    return {
        "status": "ok",
        "service": "LangGraph Chat",
        "graph_loaded": graph is not None
    }


app.include_router(auth_controller.router, prefix="/api")
app.include_router(shop_controller.router, prefix="/api")
app.include_router(product_controller.router, prefix="/api")
app.include_router(category_controller.router, prefix="/api")
app.include_router(order_controller.router, prefix="/api")
