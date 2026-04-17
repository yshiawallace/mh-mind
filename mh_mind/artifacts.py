from pathlib import Path

from mh_mind.chat import ChatResponse


def save_transcript(transcript: list[tuple[str, ChatResponse]], topic: str) -> Path:
    raise NotImplementedError
