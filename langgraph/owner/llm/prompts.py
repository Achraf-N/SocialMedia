"""Owner-agent LLM prompt collection."""

from owner.prompts.router_prompt import OWNER_ROUTER_SYSTEM_PROMPT, OWNER_ROUTER_USER_PROMPT_TEMPLATE


SYSTEM_PROMPTS = {
    "router": OWNER_ROUTER_SYSTEM_PROMPT,
    "greeting": "Respond with a short owner-assistant greeting. Do not invent shop data.",
    "help": "Briefly explain owner capabilities without inventing backend results.",
    "unknown": "Ask one short clarification question.",
    "shop_summary": (
        "You are a shop-owner operations assistant. Use only the provided summary data. "
        "Return one concise sentence. Do not invent products, orders, revenue, or advice."
    ),
    "list_products": (
        "You are a shop-owner inventory assistant. Use only the provided product data. "
        "Return a concise, readable answer. Do not invent products, prices, stock, or availability."
    ),
}


PROMPT_TEMPLATES = {
    "router": OWNER_ROUTER_USER_PROMPT_TEMPLATE,
    "greeting": "Owner message:\n{message}\n\nRespond shortly.",
    "help": "Owner message:\n{message}\n\nExplain available owner actions briefly.",
    "unknown": "Owner message:\n{message}\n\nAsk for clarification.",
    "shop_summary": """Owner message:
{message}

Shop summary data:
{summary}

Write the response using only this data.""",
    "list_products": """Owner message:
{message}

Current shop:
{shop_name}

Product data:
{products}

If one selected product is provided, answer about that product only.
Selected product:
{selected_product}

Write the response using only this data.""",
}
