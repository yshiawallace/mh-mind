"""Token-based text chunker.

Splits text into chunks of CHUNK_SIZE_TOKENS tokens with CHUNK_OVERLAP_TOKENS
overlap. Uses the nomic model's tokenizer so token counts match the embedder.
"""

from dataclasses import dataclass

from transformers import AutoTokenizer

from mh_mind.config import CHUNK_OVERLAP_TOKENS, CHUNK_SIZE_TOKENS, EMBEDDING_MODEL

# Load the tokenizer once (lightweight — no model weights)
_tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL, trust_remote_code=True)


@dataclass
class Chunk:
    text: str
    source: str  # "notes" or "docs"
    source_id: str  # note ID or file path
    position: int  # chunk index within the source document
    metadata: dict  # title, folder, date, etc.


def chunk_text(
    text: str,
    source: str,
    source_id: str,
    metadata: dict,
    chunk_size: int = CHUNK_SIZE_TOKENS,
    chunk_overlap: int = CHUNK_OVERLAP_TOKENS,
) -> list[Chunk]:
    """Split text into token-based chunks with overlap.

    Short texts that fit within chunk_size are returned as a single chunk.

    Args:
        text: The full document text.
        source: Source type ("notes" or "docs").
        source_id: Unique identifier for the source document.
        metadata: Extra metadata (title, folder, date, etc.).
        chunk_size: Max tokens per chunk.
        chunk_overlap: Number of overlapping tokens between consecutive chunks.

    Returns:
        List of Chunk dataclasses.
    """
    if not text.strip():
        return []

    token_ids = _tokenizer.encode(text, add_special_tokens=False)

    # If the whole text fits in one chunk, return it as-is
    if len(token_ids) <= chunk_size:
        return [Chunk(text=text.strip(), source=source, source_id=source_id, position=0, metadata=metadata)]

    chunks: list[Chunk] = []
    step = chunk_size - chunk_overlap
    position = 0

    for start in range(0, len(token_ids), step):
        end = min(start + chunk_size, len(token_ids))
        chunk_ids = token_ids[start:end]
        chunk_text_str = _tokenizer.decode(chunk_ids, skip_special_tokens=True).strip()

        if chunk_text_str:
            chunks.append(Chunk(
                text=chunk_text_str,
                source=source,
                source_id=source_id,
                position=position,
                metadata=metadata,
            ))
            position += 1

        # Stop if we've reached the end
        if end >= len(token_ids):
            break

    return chunks
