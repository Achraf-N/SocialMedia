# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Run the backend

```bash
cd backend
python -m uvicorn app.main:app --reload
```

The API is at `http://localhost:8000`. Interactive docs at `/docs`.

### Run a standalone LangGraph test

```bash
cd langgraph
python -m lg_app.runner
```

Or run a specific test file:

```bash
cd langgraph
python test_backend_integration.py
python test_order_agent.py
```

### Populate test data

```bash
cd backend
python populate_test_data.py
```

### Install dependencies

```bash
# Root venv (used for everything)
pip install -r requirements.txt
```

## Environment setup

Copy `.env.example` to `.env` at the project root and fill in values. Required:
- `JWT_SECRET` — any long random string
- Supabase S3 vars — only needed for product image uploads

MongoDB defaults to `mongodb://localhost:27017` with DB `socialmedia`. Ollama defaults to `http://localhost:11434` (used by the LLM router, falls back to deterministic if unavailable).

## Architecture

### Project layout

```
SocialMedia/
├── backend/app/          # FastAPI application
│   ├── controllers/      # Route handlers (auth, shop, product, category, order, chat)
│   ├── core/             # config, database, security, dependencies
│   ├── models/           # Pydantic models
│   ├── views/            # Serialization helpers
│   └── langgraph_bridge.py  # Injects langgraph/ into sys.path and re-exports build_graph
├── langgraph/lg_app/     # LangGraph chatbot (importable as lg_app.*)
│   ├── graph.py          # Compiled StateGraph — single entry point
│   ├── state.py          # ChatState TypedDict
│   ├── nodes/            # One file per graph node
│   ├── memory/           # session_store.py — MongoDB-backed session persistence
│   ├── utils/            # product_matcher.py — fuzzy product name matching
│   ├── prompts/          # router_prompt.py — system/user prompts for LLM router
│   └── llm/              # Ollama wrapper
└── requirements.txt
```

### Backend (FastAPI + MongoDB)

Multi-tenant e-commerce API. An **owner** registers and creates one or more **shops**. Each shop has **products**, **categories**, and **orders** — all scoped to `shop_id`.

- Auth is JWT-based (custom implementation, no third-party lib). Tokens are issued as HTTP-only cookies; the `Authorization: Bearer` header also works for API clients.
- Passwords use PBKDF2-SHA256 with 260 000 iterations.
- Product images are uploaded to Supabase S3-compatible storage; the public URL is saved on the product document.
- `orders_collection` has two routers: `router` (prefixed `/shops/{shop_id}/orders`) for authenticated owner use, and `orders_router` (prefixed `/orders`) for unauthenticated chatbot use. Order creation atomically decrements `product.stock` and sets `available=False` when stock hits 0, with rollback on failure.

### Chat endpoint

`POST /api/chat` receives `{message, session_id, shop_id}`, builds a `ChatState`, runs `graph.invoke(state)`, and returns the result. The LangGraph code lives in `langgraph/` and is loaded at startup via `langgraph_bridge.py`, which does `sys.path.insert(0, "<project>/langgraph")`.

### LangGraph workflow

Graph flow: `load_shop_data → load_session_state → intent_router → update_active_product → <agent node> → save_session_state → END`

**Intent routing** (`nodes/router.py`):
1. First tries Ollama (`qwen3:8b`) with a structured JSON prompt.
2. Falls back to `deterministic_intent_router` (keyword matching) if Ollama is unavailable or returns invalid JSON.
3. `_apply_sales_priority` then applies hard overrides on top of either result (e.g. catalog phrases always win, greeting word-boundary checks, pending-order field-reply detection).

**Supported intents** (13 total): `greeting`, `small_talk`, `product_list`, `product_info_question`, `shop_info_question`, `availability_question`, `order_intent`, `order_creation`, `order_status`, `price_question`, `delivery_question`, `payment_question`, `complaint`/`human_needed`.

**Session state** (`memory/session_store.py`): Stores `active_product`, `pending_order_json`, `delivery_city`, `last_catalog_products`, etc. per `(session_id, shop_id)` pair. Prefers MongoDB `chat_sessions` collection; falls back to a local JSON file (`langgraph/.chat_sessions.json`), then in-memory dict.

**Order flow**: The `order_agent` node extracts customer fields (name, phone, city, delivery_address) from natural language, merges them into `pending_order_json` across turns, and calls `POST /api/orders` once all fields are present.

**Multilingual**: The router and agent nodes include Moroccan Darija terms (e.g. `bghit`, `ch7al`, `katsifto`) alongside English and French keywords.

### Key data flow

- `load_shop_data` fetches the shop's products from MongoDB into `state["shop_data"]` on every turn.
- `update_active_product` resolves `product_query` (set by the router) into `active_product_id` and `active_product_name` on the state before any agent node runs.
- Agent nodes read `state["shop_data"]` to answer questions — they do not call the backend API directly (except `order_agent` and `order_status_agent`).
