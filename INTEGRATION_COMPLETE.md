# Integration Complete: One API, One URL

## What Changed?

✅ **Before:** 2 APIs on 2 different ports
- Backend API: http://localhost:8000
- LangGraph API: http://localhost:5000

✅ **After:** 1 Unified API
- Backend API (with integrated LangGraph): http://localhost:8000

---

## Architecture

```
┌─────────────────────────────────────┐
│   Frontend (React/Vue)              │
│   http://localhost:3000             │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│   Backend API (FastAPI)             │
│   http://localhost:8000             │
├─────────────────────────────────────┤
│  /api/shops                         │
│  /api/shops/{id}/products           │
│  /api/categories                    │
│  /api/auth                          │
│  /api/chat      ← LangGraph chat!   │
│  /api/chat/health                   │
├─────────────────────────────────────┤
│  MongoDB                            │
│  Ollama LLM                         │
└─────────────────────────────────────┘
```

---

## New Endpoints

### Chat Endpoint (LangGraph)
```
POST /api/chat

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
```

### Chat Health
```
GET /api/chat/health

Response:
{
  "status": "ok",
  "service": "LangGraph Chat",
  "graph_loaded": true
}
```

---

## Startup

Now just one command:

```bash
# Option 1: PowerShell
.\start_all.ps1

# Option 2: Batch
start_all.bat

# Option 3: Python
python start_services.py

# Option 4: Manual
cd backend
uvicorn app.main:app --reload --port 8000
```

Everything runs on **http://localhost:8000**

---

## Migration from Separate APIs

### Old Frontend Code
```javascript
// Chat request to separate API
fetch('http://localhost:5000/chat', {
  method: 'POST',
  body: JSON.stringify({...})
})
```

### New Frontend Code
```javascript
// Chat request to unified API
fetch('http://localhost:8000/api/chat', {
  method: 'POST',
  body: JSON.stringify({...})
})
```

---

## File Structure

```
backend/
├── app/
│   ├── main.py              ← Now includes LangGraph chat route
│   ├── controllers/
│   │   ├── chat_controller.py       ← NEW: Chat endpoint
│   │   ├── product_controller.py
│   │   ├── shop_controller.py
│   │   ├── category_controller.py
│   │   └── auth_controller.py
│   ├── models/
│   ├── core/
│   └── ...
└── requirements.txt

langgraph/
├── app/
│   ├── graph.py             ← Workflow logic
│   ├── nodes/               ← Agent implementations
│   ├── state.py             ← State definitions
│   ├── memory/              ← Session management
│   ├── api/
│   │   └── backend_client.py    ← Calls /api/shops/{id}/products
│   └── ...
└── ...

start_all.bat/ps1/py        ← Now starts only backend
```

---

## Why This Is Better

1. **Simpler Architecture** - One API, one port
2. **Single Deployment** - Deploy once, not twice
3. **Shared Authentication** - JWT tokens work for all endpoints
4. **CORS Friendly** - All endpoints same origin
5. **Easier Integration** - Frontend calls one URL
6. **Better Maintenance** - One codebase to manage

---

## Testing

### Old Way (2 APIs)
```bash
# Terminal 1
cd backend; uvicorn app.main:app --port 8000

# Terminal 2
cd langgraph; python -m app.api.server
```

### New Way (1 API)
```bash
# Terminal 1
cd backend; uvicorn app.main:app --port 8000
```

Test:
```bash
curl http://localhost:8000/api/chat \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What products do you have?",
    "session_id": "user123",
    "shop_id": "6a09d431697b1d38b68a50ce"
  }'
```

---

## API Documentation

Access FastAPI auto-generated docs:

```
http://localhost:8000/docs
```

This shows all endpoints including:
- ✓ /api/chat
- ✓ /api/shops
- ✓ /api/products
- ✓ /api/auth
- ✓ /api/categories

---

## Backward Compatibility

The old separate Flask server (`app/api/server.py`) still exists but is **no longer needed**.

You can:
- ✓ Keep it for reference
- ✓ Delete if you prefer clean codebase

The functionality is now in `backend/app/controllers/chat_controller.py`

---

## Environment Variables

Update your `.env`:

```env
# Before
BACKEND_URL=http://localhost:8000
FLASK_PORT=5000

# After (no change needed!)
BACKEND_URL=http://localhost:8000
# Just remove FLASK_PORT, it's not used anymore
```

---

## Next: Frontend Integration

Update your frontend to call the unified API:

```javascript
// React example
const response = await fetch('/api/chat', {  // Changed from localhost:5000
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    message: userMessage,
    session_id: userId,
    shop_id: shopId
  })
});
```

---

## Questions?

- **Where's the chat endpoint?** `backend/app/controllers/chat_controller.py`
- **How does it access products?** Via `app.api.backend_client.get_shop_with_products()`
- **Why integrate?** Simpler architecture, single deployment, one URL
- **Keep the old Flask server?** Optional - it's still there but not used
