"""LLM provider abstraction with OpenRouter as the default backend."""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from openai import OpenAI

from mh_mind.config import DEFAULT_LLM_MODEL


@dataclass
class Message:
    role: str  # "system", "user", or "assistant"
    content: str


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, messages: list[Message], temperature: float = 0.3) -> str:
        """Send messages to the LLM and return the assistant's response text."""
        ...


class OpenRouterProvider(LLMProvider):
    """OpenRouter-backed LLM provider (OpenAI-compatible API)."""

    def __init__(self, model: str = DEFAULT_LLM_MODEL, api_key: str | None = None):
        self.model = model
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key or os.environ.get("OPENROUTER_API_KEY", ""),
        )

    def complete(self, messages: list[Message], temperature: float = 0.3) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
        )
        return response.choices[0].message.content or ""


# Default provider instance — lazy so import doesn't require the API key
_default_provider: LLMProvider | None = None


def get_provider() -> LLMProvider:
    """Get or create the default LLM provider."""
    global _default_provider
    if _default_provider is None:
        _default_provider = OpenRouterProvider()
    return _default_provider
