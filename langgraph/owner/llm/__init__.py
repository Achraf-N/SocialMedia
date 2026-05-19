"""Ollama LLM integration for the owner agent."""

from typing import Optional

import requests


class OllamaLLM:
    """Small Ollama client used by owner-agent nodes."""

    def __init__(self, model: str = "gemma4:31b-cloud", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"

    def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 256,
        system: Optional[str] = None,
    ) -> str:
        full_prompt = prompt if system is None else f"{system}\n\n{prompt}"
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "think": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        try:
            response = requests.post(self.api_url, json=payload, timeout=20)
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Could not connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running: ollama serve"
            )
        except Exception as exc:
            raise RuntimeError(f"Ollama error: {str(exc)}")


_llm_instance: Optional[OllamaLLM] = None


def get_llm(model: str = "gemma4:31b-cloud") -> OllamaLLM:
    """Get or create the owner-agent Ollama client."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = OllamaLLM(model=model)
    return _llm_instance
