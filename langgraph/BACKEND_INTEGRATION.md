# LangGraph + Backend API Integration Guide

## Overview

Your LangGraph chatbot now integrates with your backend API to fetch real product data.

```
Frontend (React/Vue)
    ↓ POST /chat
Flask API Server (Port 5000)
    ↓ get_shop_with_products()
Backend API (Port 8000)
    GET /api/shops/{shop_id}/products
    ↓
MongoDB
```

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Backend API

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 3. Start LangGraph API Server

```bash
cd langgraph
python -m app.api.server
```

The server runs on `http://localhost:5000`

---

## API Endpoints

### Health Check
```
GET /health

Response:
{
  "status": "ok",
  "service": "LangGraph Chatbot"
}
```

### Configuration
```
POST /config

Request:
{
  "backend_url": "http://localhost:8000",
  "jwt_token": "eyJ0eXAi..."  // optional
}

Response:
{
  "status": "configured"
}
```

### Chat
```
POST /chat

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

---

## Frontend Integration (JavaScript/React)

```javascript
// Example: React component
import { useState } from 'react';

export function ChatWidget() {
  const [message, setMessage] = useState('');
  const [responses, setResponses] = useState([]);
  
  // Your shop ID from backend
  const SHOP_ID = '6a09d431697b1d38b68a50ce';
  const SESSION_ID = 'user123'; // or generate unique ID
  
  async function sendMessage() {
    try {
      const response = await fetch('http://localhost:5000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${userToken}` // optional JWT
        },
        body: JSON.stringify({
          message: message,
          session_id: SESSION_ID,
          shop_id: SHOP_ID
        })
      });
      
      const data = await response.json();
      setResponses([...responses, {
        user: message,
        bot: data.response,
        intent: data.intent
      }]);
      setMessage('');
    } catch (error) {
      console.error('Error:', error);
    }
  }
  
  return (
    <div className="chat">
      <div className="messages">
        {responses.map((r, i) => (
          <div key={i}>
            <p className="user">You: {r.user}</p>
            <p className="bot">Bot: {r.bot}</p>
          </div>
        ))}
      </div>
      <input 
        value={message} 
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Type message..."
      />
      <button onClick={sendMessage}>Send</button>
    </div>
  );
}
```

---

## Flow: How Messages Are Processed

1. **Frontend** sends: `"What is the price of string?"`
2. **Flask Server** receives and creates ChatState with `shop_id`
3. **load_shop_data** calls: `GET /api/shops/{shop_id}/products`
4. **Backend API** returns shop info + products from MongoDB
5. **Router** detects intent: `price_question`
6. **Price Agent** finds product and generates response
7. **Flask Server** returns to frontend

---

## Data Flow in LangGraph

### ChatState Structure

```python
{
  "session_id": "user123",
  "shop_id": "6a09d431697b1d38b68a50ce",  # NEW: Required for backend
  "message": "What is the price?",
  "intent": "price_question",
  "product_query": "string",
  "active_product": "string",
  "response": "string is 0 MAD",
  "steps": ["Loaded 3 products from backend", ...],
  "shop_data": [
    {
      "id": "6a09ddf746a9e8da6137e161",
      "name": "string",
      "price": 0,
      "description": "string",
      "available": true,
      "category": "string",
      "stock": 0,
      "brand": "string",
      ...
    }
  ],
  "needs_human": false,
  "confidence": 0.95
}
```

---

## Configuration

### .env File (Optional)

```env
BACKEND_URL=http://localhost:8000
FLASK_PORT=5000
JWT_SECRET=your-secret-key
```

### Environment Variables in Code

```python
from app.api import set_backend_url, set_jwt_token
import os

set_backend_url(os.getenv("BACKEND_URL", "http://localhost:8000"))
if os.getenv("JWT_TOKEN"):
    set_jwt_token(os.getenv("JWT_TOKEN"))
```

---

## Testing

### Test Backend Client

```bash
python test_backend_integration.py
```

This tests:
- ✓ Connection to backend
- ✓ Fetching products
- ✓ Searching products
- ✓ Getting shop info

### Manual Testing

```bash
# Terminal 1: Start backend
cd backend && uvicorn app.main:app --reload

# Terminal 2: Start LangGraph API
cd langgraph && python -m app.api.server

# Terminal 3: Test chat
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What products do you have?",
    "session_id": "user123",
    "shop_id": "6a09d431697b1d38b68a50ce"
  }'
```

---

## Authentication (JWT)

If your backend requires JWT:

```python
# Set token at startup
from app.api import set_jwt_token
set_jwt_token("eyJ0eXAiOiJKV1QiLCJhbGc...")

# Or in frontend
fetch('http://localhost:5000/chat', {
  headers: {
    'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGc...'
  }
})
```

---

## File Structure

```
langgraph/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── backend_client.py      # Backend API client
│   │   ├── server.py              # Flask API server
│   │   └── CONFIG.md              # Configuration guide
│   ├── nodes/
│   │   └── load_shop_data.py      # Updated to use backend
│   ├── state.py                   # Updated with shop_id
│   └── graph.py
├── test_backend_integration.py    # Test backend connection
└── requirements.txt               # Updated with flask, requests
```

---

## Troubleshooting

### Error: "Connection refused"
- Make sure backend is running on port 8000
- Check `set_backend_url()` is using correct URL

### Error: "shop_id not found"
- Replace `6a09d431697b1d38b68a50ce` with your actual shop ID
- Verify shop exists in your MongoDB

### Error: "Unauthorized"
- Backend requires JWT authentication
- Call `set_jwt_token()` with valid token

### No products returned
- Check shop_id is correct
- Verify products exist in backend database

---

## Next Steps

1. ✅ Backend API set up
2. ✅ LangGraph integration created
3. ⬜ Frontend integration (build your UI)
4. ⬜ Deploy to production
