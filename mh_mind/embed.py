"""Embeddings via OpenAI text-embedding-3-large (3,072-dim).

Chunk text is sent to OpenAI's API for embedding. The full corpus
stays local — only individual chunks are sent per API call.
"""

import logging
import os

from openai import OpenAI

from mh_mind.config import EMBEDDING_DIM, EMBEDDING_MODEL

logger = logging.getLogger(__name__)

_BATCH_SIZE = 2048  # OpenAI API max inputs per call

# Lazy-loaded singleton client
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Add it to your .env file or environment."
            )
        _client = OpenAI(api_key=api_key, max_retries=3)
    return _client


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed a batch of document chunks for storage.

    Args:
        texts: List of chunk texts.

    Returns:
        List of 3,072-dim embedding vectors.
    """
    if not texts:
        return []

    client = _get_client()
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        all_embeddings.extend([item.embedding for item in response.data])

    return all_embeddings


def embed_query(text: str) -> list[float]:
    """Embed a single user query for retrieval.

    Args:
        text: The user's question.

    Returns:
        A single 3,072-dim embedding vector.
    """
    client = _get_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=[text])
    return response.data[0].embedding
