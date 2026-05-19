"""Owner-agent LLM prompt collection."""

from owner.prompts.router_prompt import OWNER_ROUTER_SYSTEM_PROMPT, OWNER_ROUTER_USER_PROMPT_TEMPLATE


SYSTEM_PROMPTS = {
    "router": OWNER_ROUTER_SYSTEM_PROMPT,
    "greeting": "Respond with a short owner-assistant greeting.",
    "help": "Briefly explain owner capabilities without inventing backend results.",
    "unknown": "Ask one short clarification question.",
}


PROMPT_TEMPLATES = {
    "router": OWNER_ROUTER_USER_PROMPT_TEMPLATE,
    "greeting": "Owner message:\n{message}\n\nRespond shortly.",
    "help": "Owner message:\n{message}\n\nExplain available owner actions briefly.",
    "unknown": "Owner message:\n{message}\n\nAsk for clarification.",
}
