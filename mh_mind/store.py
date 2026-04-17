from pathlib import Path

from mh_mind.chunk import Chunk


def init_db(db_path: Path) -> None:
    raise NotImplementedError


def upsert_chunks(db_path: Path, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
    raise NotImplementedError


def search(db_path: Path, query_embedding: list[float], scope: str, top_k: int) -> list[Chunk]:
    raise NotImplementedError
