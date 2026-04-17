from mh_mind.chunk import Chunk


def retrieve(query: str, scope: str = "both", top_k: int = 10) -> list[Chunk]:
    raise NotImplementedError
