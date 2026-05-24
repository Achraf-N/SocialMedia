# LangGraph Agent — System Schema

## Graph Execution Flow

```
POST /api/chat  {message, session_id, shop_id}
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│                   LANGGRAPH GRAPH                       │
│                                                         │
│  1. load_shop_data                                      │
│     ├─ Direct MongoDB read (when inside backend app)    │
│     ├─ HTTP GET /api/shops/{shop_id}/products           │
│     └─ Fallback → mock data                             │
│              │                                          │
│  2. load_session_state                                  │
│     └─ Reads (session_id, shop_id) from:               │
│        MongoDB chat_sessions → JSON file → in-memory   │
│        Restores: active_product, pending_order_json,    │
│                  delivery_city, last_catalog_products   │
│              │                                          │
│  3. intent_router                                       │
│     ├─ Try Ollama (qwen3:8b) → structured JSON         │
│     │   └─ on failure → deterministic fallback          │
│     └─ _apply_sales_priority (hard overrides always)   │
│        Sets: intent, product_query, confidence,         │
│              delivery_city, delivery_address            │
│              │                                          │
│  4. update_active_product                               │
│     └─ Resolves product_query → active_product_id      │
│        using fuzzy matching (product_matcher.py)        │
│              │                                          │
│  5. route_by_intent  (conditional edge)                 │
│     │                                                   │
│     ├─ greeting          → greeting_agent               │
│     ├─ small_talk        → small_talk_agent             │
│     ├─ product_list      → product_list_agent           │
│     ├─ product_info_question  ┐                         │
│     ├─ availability_question  ┘→ product_info_agent     │
│     ├─ price_question    → price_agent                  │
│     ├─ delivery_question → delivery_agent               │
│     ├─ payment_question  → payment_agent                │
│     ├─ shop_info_question → shop_info_agent             │
│     ├─ order_intent      ┐                              │
│     ├─ order_creation    ┘→ order_agent                 │
│     ├─ order_status      → order_status_agent           │
│     ├─ complaint         ┐                              │
│     ├─ human_needed      ┘→ human_needed_agent          │
│     └─ unknown           → unknown_agent                │
│              │                                          │
│  6. save_session_state                                  │
│     └─ Persists: active_product, pending_order_json,   │
│                  delivery_city, last_catalog_products   │
│              │                                          │
│             END                                         │
└─────────────────────────────────────────────────────────┘
        │
        ▼
   state["response"]  → returned to client
```

---

## Intent Router — Decision Priority

```
User message
     │
     ▼
[Ollama qwen3:8b] ──fails──► [deterministic keyword match]
     │                              │
     └──────────────────────────────┘
                   │
                   ▼
        _apply_sales_priority (always runs, overrides LLM/deterministic)

Priority chain (first match wins):
  1. shop info phrase        → shop_info_question
  2. catalog/all-products    → product_list
  3. catalog index ref       → product_info_question  ("the second one")
  4. greeting word-boundary  → greeting
  5. pending order confirm   → order_creation
  6. small talk word-boundary → small_talk
  7. order status signal     → order_status
  8. complaint terms         → complaint + needs_human=True
  9. human/support terms     → human_needed
 10. pending order + field reply → order_creation
 11. explicit order phrase   → order_creation
 12. delivery terms          → delivery_question
 13. payment terms           → payment_question
 14. price terms             → price_question
 15. availability terms      → availability_question
 16. order terms             → order_creation
 17. product mention + info terms → product_info_question
 18. (LLM/deterministic result kept if nothing matched)
```

---

## Order Agent — Multi-turn State Machine

```
order_agent(state)
     │
     ├─ "cancel/stop" in message?
     │    └─ clear pending_order, return
     │
     ├─ confirm_customer_info flag set?
     │    ├─ "no/wrong" → clear customer_info, ask again
     │    └─ "yes/correct" → proceed
     │
     ├─ Extract fields from message:
     │    labeled (name: X, phone: Y), phone regex, city list,
     │    name patterns, quantity patterns
     │
     ├─ Merge into pending_order_json (accumulates across turns)
     │
     ├─ Product not identified?
     │    └─ Ask "Which product?"
     │
     ├─ Customer fields missing? (name, phone, city, delivery_address)
     │    ├─ Previous order exists for this session?
     │    │    └─ Propose saved info → set confirm_customer_info flag
     │    └─ Ask for missing fields
     │
     └─ All fields present → POST /api/orders (via backend_client)
          ├─ Success → clear pending_order_json, return confirmation
          └─ Failure → return error message
```

---

## ChatState — Key Fields

| Field | Purpose |
|---|---|
| `session_id`, `shop_id` | Scope for all lookups |
| `message` | Raw user input |
| `intent` | Detected intent (13 possible values) |
| `product_query` | Product name extracted from message |
| `active_product_id/name` | Resolved product after fuzzy match |
| `pending_order_json` | Accumulated order fields across turns |
| `delivery_city/address` | Extracted location (survives turns) |
| `last_catalog_products` | Product names from last list response |
| `confidence` | Router confidence score (0–1) |
| `needs_human` | Flag to escalate to human support |
| `shop_data` | All products for this shop (loaded fresh each turn) |
| `response` | Final text returned to client |

---

## Session Persistence — Storage Cascade

```
save/load session state
      │
      ├─ 1st: MongoDB chat_sessions (preferred, shared across instances)
      ├─ 2nd: .chat_sessions.json  (file fallback)
      └─ 3rd: in-memory dict       (last resort, lost on restart)
```
