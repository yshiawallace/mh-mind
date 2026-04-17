import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from openai import OpenAI

from mh_mind.config import DEFAULT_LLM_MODEL


@dataclass
class Message:
    role: str
    content: str


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, messages: list[Message]) -> str:
        ...


class OpenRouterProvider(LLMProvider):
    def __init__(self, model: str = DEFAULT_LLM_MODEL, api_key: str | None = None):
        self.model = model
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key or os.environ["OPENROUTER_API_KEY"],
        )

    def complete(self, messages: list[Message]) -> str:
        raise NotImplementedError
