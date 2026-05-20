"""Shared LLM response helper for owner nodes."""

from owner.llm import get_llm
from owner.llm.prompts import PROMPT_TEMPLATES, SYSTEM_PROMPTS


def generate_owner_response(prompt_key: str, **kwargs) -> str | None:
    """Generate an owner response with Ollama, returning None on fallback."""
    try:
        prompt = PROMPT_TEMPLATES[prompt_key].format(**kwargs)
        response = get_llm().generate(
            prompt=prompt,
            system=SYSTEM_PROMPTS[prompt_key],
            temperature=0.3,
            max_tokens=256,
        )
        return response.strip() or None
    except Exception:
        return None
