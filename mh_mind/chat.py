from dataclasses import dataclass

from mh_mind.chunk import Chunk


@dataclass
class ChatResponse:
    answer: str
    sources: list[Chunk]


def answer(query: str, scope: str = "both") -> ChatResponse:
    raise NotImplementedError
