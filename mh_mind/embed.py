"""Local embedding using nomic-ai/nomic-embed-text-v1.5.

The model runs entirely on-CPU — your corpus never leaves the machine.
Vectors are 768-dimensional.

Important: nomic models require task prefixes:
  - "search_document: " when embedding chunks for storage
  - "search_query: " when embedding the user's question
Omitting these prefixes silently degrades retrieval quality.
"""

import logging

from sentence_transformers import SentenceTransformer

from mh_mind.config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 768

# Lazy-loaded singleton — the model is ~500 MB and takes a few seconds to load,
# so we only do it once and only when actually needed.
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading embedding model %s (first call, may take a moment)...", EMBEDDING_MODEL)
        _model = SentenceTransformer(EMBEDDING_MODEL, trust_remote_code=True)
        logger.info("Embedding model loaded.")
    return _model


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed a batch of document chunks for storage.

    Prepends the 'search_document: ' prefix required by nomic models.

    Args:
        texts: List of chunk texts.

    Returns:
        List of 768-dim embedding vectors.
    """
    if not texts:
        return []

    model = _get_model()
    prefixed = [f"search_document: {t}" for t in texts]
    embeddings = model.encode(prefixed, show_progress_bar=len(texts) > 50)
    return [e.tolist() for e in embeddings]


def embed_query(text: str) -> list[float]:
    """Embed a single user query for retrieval.

    Prepends the 'search_query: ' prefix required by nomic models.

    Args:
        text: The user's question.

    Returns:
        A single 768-dim embedding vector.
    """
    model = _get_model()
    prefixed = f"search_query: {text}"
    embedding = model.encode([prefixed])
    return embedding[0].tolist()
