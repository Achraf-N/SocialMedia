"""LangGraph chat controller - integrated into backend API."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List

# Import from bridge module that handles LangGraph path setup
try:
    from app.langgraph_bridge import build_graph, ChatState
except Exception as e:
    print(f"ERROR: Failed to import LangGraph: {e}")
    print("Make sure the langgraph directory is in the correct location")
    build_graph = None
    ChatState = None

from app.core.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize LangGraph graph
graph = None
if build_graph is not None:
    try:
        graph = build_graph()
        print("✓ LangGraph graph initialized successfully")
    except Exception as e:
        print(f"⚠ Warning: Failed to initialize LangGraph graph: {e}")
        print("  Chat endpoint will return error until this is fixed")


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    session_id: str
    shop_id: str


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    intent: Optional[str] = None
    active_product: Optional[str] = None
    session_id: str
    confidence: float
    steps: List[str] = []


@router.post("", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint - integrated LangGraph workflow.
    
    This endpoint:
    1. Receives user message
    2. Loads products from this backend (/api/shops/{shop_id}/products)
    3. Routes intent using LangGraph
    4. Generates response using LLM
    5. Maintains session state
    
    Request:
    {
        "message": "What is the price of string?",
        "session_id": "user123",
        "shop_id": "6a09d431697b1d38b68a50ce"
    }
    
    Response:
    {
        "response": "string is 0 MAD",
        "intent": "price_question",
        "active_product": "string",
        "session_id": "user123",
        "confidence": 0.95,
        "steps": [...]
    }
    """
    try:
        # Check if dependencies are initialized
        if graph is None or ChatState is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LangGraph chat service not initialized. Check server logs."
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
        
        return ChatResponse(
            response=result.get("response", "I couldn't process your request"),
            intent=result.get("intent"),
            active_product=result.get("active_product"),
            session_id=request.session_id,
            confidence=result.get("confidence", 0.0),
            steps=result.get("steps", [])
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing error: {str(e)}"
        )


@router.get("/health", tags=["health"])
def chat_health() -> dict:
    """Check chat service is ready."""
    return {
        "status": "ok",
        "service": "LangGraph Chat",
        "graph_loaded": graph is not None
    }
