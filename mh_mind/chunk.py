from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    source: str
    source_id: str
    position: int
    metadata: dict


def chunk_text(text: str, source: str, source_id: str, metadata: dict) -> list[Chunk]:
    raise NotImplementedError
