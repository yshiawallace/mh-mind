"""Retrieve relevant chunks from the corpus for a given query."""

from mh_mind.config import CORPUS_DB
from mh_mind.embed import embed_query
from mh_mind.store import search


def retrieve(query: str, scope: str = "both", top_k: int = 10) -> list[dict]:
    """Embed the query and return the top_k most relevant chunks.

    Args:
        query: The user's question.
        scope: "notes", "docs", or "both".
        top_k: Number of results.

    Returns:
        List of dicts with keys: text, source, source_id, position, metadata, distance.
    """
    if scope not in ("notes", "docs", "both"):
        raise ValueError(f"scope must be 'notes', 'docs', or 'both', got {scope!r}")

    query_vec = embed_query(query)
    return search(CORPUS_DB, query_vec, scope=scope, top_k=top_k)
