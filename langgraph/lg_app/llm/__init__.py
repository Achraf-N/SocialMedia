"""Ollama LLM integration module."""

import requests
from typing import Optional


class OllamaLLM:
    """Interface to Ollama local LLM."""
    
    def __init__(self, model: str = "gemma4:31b-cloud", base_url: str = "http://localhost:11434"):
        """
        Initialize Ollama LLM client.
        
        Args:
            model: Model name (default: gemma4:31b-cloud)
            base_url: Ollama API base URL (default: http://localhost:11434)
        """
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 256,
        system: Optional[str] = None,
    ) -> str:
        """
        Generate response from Ollama.
        
        Args:
            prompt: Input prompt
            temperature: Temperature for generation (0-1)
            max_tokens: Maximum tokens to generate
            system: System prompt for context
            
        Returns:
            Generated text response
        """
        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"
        
        try:
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
            
            response = requests.post(self.api_url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "").strip()
        
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Could not connect to Ollama at {self.base_url}. "
                f"Make sure Ollama is running: ollama serve"
            )
        except Exception as e:
            raise RuntimeError(f"Ollama error: {str(e)}")


# Global LLM instance
_llm_instance: Optional[OllamaLLM] = None


def get_llm(model: str = "gemma4:31b-cloud") -> OllamaLLM:
    """Get or create Ollama LLM instance."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = OllamaLLM(model=model)
    return _llm_instance
