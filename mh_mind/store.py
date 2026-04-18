"""SQLite + sqlite-vec vector store.

Stores chunks with metadata in a regular table and their embeddings in a
vec0 virtual table. Both tables are joined by rowid.
"""

import json
import sqlite3
import struct
from contextlib import contextmanager, nullcontext
from pathlib import Path

import sqlite_vec

from mh_mind.chunk import Chunk
from mh_mind.config import EMBEDDING_DIM


def _serialize_f32(vec: list[float]) -> bytes:
    """Serialize a float list to a compact binary format for sqlite-vec."""
    return struct.pack(f"{len(vec)}f", *vec)


@contextmanager
def connect(db_path: Path):
    """Open a connection with the sqlite-vec extension loaded."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Path) -> None:
    """Create the chunks and embedding tables if they don't exist."""
    with connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                position INTEGER NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_source
            ON chunks(source)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_source_id
            ON chunks(source_id)
        """)
        # Track which source documents have been ingested, for incremental sync
        conn.execute("""
            CREATE TABLE IF NOT EXISTS source_files (
                source_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                last_synced TEXT NOT NULL
            )
        """)
        assert isinstance(EMBEDDING_DIM, int)
        conn.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunk_embeddings USING vec0(
                embedding float[{EMBEDDING_DIM}]
            )
        """)
        conn.commit()


def upsert_chunks(
    db_path: Path,
    chunks: list[Chunk],
    embeddings: list[list[float]],
    conn: sqlite3.Connection | None = None,
) -> None:
    """Insert or replace chunks and their embeddings transactionally.

    All existing chunks for the same source_id are deleted first
    (a source document is re-chunked as a whole unit).
    """
    if not chunks:
        return
    if len(chunks) != len(embeddings):
        raise ValueError(f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) must be the same length")

    with nullcontext(conn) if conn else connect(db_path) as conn:
        # Group chunks by source_id to delete old versions
        source_ids = {c.source_id for c in chunks}

        for sid in source_ids:
            # Find existing rowids for this source_id so we can delete from both tables
            rows = conn.execute("SELECT id FROM chunks WHERE source_id = ?", (sid,)).fetchall()
            old_ids = [r["id"] for r in rows]
            if old_ids:
                placeholders = ",".join("?" * len(old_ids))
                conn.execute(f"DELETE FROM chunk_embeddings WHERE rowid IN ({placeholders})", old_ids)
                conn.execute(f"DELETE FROM chunks WHERE id IN ({placeholders})", old_ids)

        # Insert new chunks and embeddings
        for chunk, emb in zip(chunks, embeddings):
            cursor = conn.execute(
                "INSERT INTO chunks (text, source, source_id, position, metadata) VALUES (?, ?, ?, ?, ?)",
                (chunk.text, chunk.source, chunk.source_id, chunk.position, json.dumps(chunk.metadata)),
            )
            rowid = cursor.lastrowid
            conn.execute(
                "INSERT INTO chunk_embeddings (rowid, embedding) VALUES (?, ?)",
                (rowid, _serialize_f32(emb)),
            )

        conn.commit()


def update_source_hash(
    db_path: Path,
    source_id: str,
    source: str,
    content_hash: str,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Record or update the content hash for a source document."""
    from datetime import datetime

    with nullcontext(conn) if conn else connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO source_files (source_id, source, content_hash, last_synced)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                content_hash = excluded.content_hash,
                last_synced = excluded.last_synced
            """,
            (source_id, source, content_hash, datetime.now().isoformat()),
        )
        conn.commit()


def get_source_hash(
    db_path: Path,
    source_id: str,
    conn: sqlite3.Connection | None = None,
) -> str | None:
    """Get the stored content hash for a source document, or None if not yet ingested."""
    with nullcontext(conn) if conn else connect(db_path) as conn:
        row = conn.execute(
            "SELECT content_hash FROM source_files WHERE source_id = ?",
            (source_id,),
        ).fetchone()
        return row["content_hash"] if row else None


def search(
    db_path: Path,
    query_embedding: list[float],
    scope: str = "both",
    top_k: int = 10,
    conn: sqlite3.Connection | None = None,
) -> list[dict]:
    """Find the top_k most similar chunks to the query embedding.

    Args:
        db_path: Path to the SQLite database.
        query_embedding: 3,072-dim query vector.
        scope: "notes", "docs", or "both".
        top_k: Number of results to return.

    Returns:
        List of dicts with keys: text, source, source_id, position, metadata, distance.
    """
    with nullcontext(conn) if conn else connect(db_path) as conn:
        serialized_query = _serialize_f32(query_embedding)

        # sqlite-vec doesn't support pre-filtering, so we overfetch and filter.
        # If the corpus is skewed (e.g. mostly notes), we may need to widen the
        # search to find enough results for the requested scope.
        fetch_k = top_k if scope == "both" else top_k * 3
        max_fetch = top_k * 50

        while True:
            rows = conn.execute(
                """
                SELECT
                    c.id, c.text, c.source, c.source_id, c.position, c.metadata,
                    v.distance
                FROM chunk_embeddings v
                JOIN chunks c ON c.id = v.rowid
                WHERE v.embedding MATCH ?
                    AND k = ?
                ORDER BY v.distance
                """,
                (serialized_query, fetch_k),
            ).fetchall()

            results = []
            for row in rows:
                if scope != "both" and row["source"] != scope:
                    continue
                results.append({
                    "text": row["text"],
                    "source": row["source"],
                    "source_id": row["source_id"],
                    "position": row["position"],
                    "metadata": json.loads(row["metadata"]),
                    "distance": row["distance"],
                })
                if len(results) >= top_k:
                    break

            # Stop if we have enough results, or if the DB returned fewer rows
            # than we asked for (meaning we've exhausted all candidates).
            if len(results) >= top_k or len(rows) < fetch_k or fetch_k >= max_fetch:
                break
            fetch_k = min(fetch_k * 2, max_fetch)

        return results
