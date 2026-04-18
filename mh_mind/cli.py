"""CLI entry points: `mh-mind sync` and `mh-mind chat`."""

import argparse
import hashlib
import logging
import sys

from mh_mind.config import (
    CORPUS_DB,
    DATA_DIR,
    load_docs_paths,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def cmd_sync(args: argparse.Namespace) -> int:
    """Ingest Apple Notes + Word docs, chunk, embed, and store."""
    from mh_mind.chunk import chunk_text
    from mh_mind.embed import embed_documents
    from mh_mind.ingest.apple_notes import export_notes
    from mh_mind.ingest.word_docs import load_docs
    from mh_mind.store import (
        connect,
        get_source_hash,
        init_db,
        update_source_hash,
        upsert_chunks,
    )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    init_db(CORPUS_DB)

    # --- Apple Notes ---
    logger.info("Ingesting Apple Notes...")
    try:
        notes = export_notes()
    except RuntimeError as e:
        logger.error("Apple Notes export failed: %s", e)
        notes = []

    # --- Word Docs ---
    logger.info("Ingesting Word documents...")
    doc_paths = load_docs_paths()
    docs = load_docs(doc_paths) if doc_paths else []

    # --- Collect changed documents and chunk them ---
    # Each entry: (chunks, source_id, source_type, content_hash)
    pending: list[tuple[list, str, str, str]] = []

    skipped_notes = 0
    skipped_docs = 0

    with connect(CORPUS_DB) as conn:
        for note in notes:
            content_hash = hashlib.sha256(note.body.encode()).hexdigest()[:16]
            stored_hash = get_source_hash(CORPUS_DB, note.id, conn=conn)

            if stored_hash == content_hash:
                skipped_notes += 1
                continue

            chunks = chunk_text(
                text=note.body,
                source="notes",
                source_id=note.id,
                metadata={
                    "title": note.title,
                    "folder": note.folder,
                    "created": note.created.isoformat(),
                    "modified": note.modified.isoformat(),
                },
            )
            if chunks:
                pending.append((chunks, note.id, "notes", content_hash))

        for doc in docs:
            content_hash = hashlib.sha256(doc.body.encode()).hexdigest()[:16]
            source_id = str(doc.path)
            stored_hash = get_source_hash(CORPUS_DB, source_id, conn=conn)

            if stored_hash == content_hash:
                skipped_docs += 1
                continue

            chunks = chunk_text(
                text=doc.body,
                source="docs",
                source_id=source_id,
                metadata={
                    "title": doc.title,
                    "path": str(doc.path),
                    "modified": doc.modified.isoformat(),
                },
            )
            if chunks:
                pending.append((chunks, source_id, "docs", content_hash))

        # --- Batch-embed all chunks in one API call ---
        all_texts = [c.text for chunks, _, _, _ in pending for c in chunks]
        all_embeddings = embed_documents(all_texts) if all_texts else []

        # --- Upsert each document's chunks with its slice of embeddings ---
        offset = 0
        for chunks, source_id, source_type, content_hash in pending:
            n = len(chunks)
            upsert_chunks(CORPUS_DB, chunks, all_embeddings[offset:offset + n], conn=conn)
            update_source_hash(CORPUS_DB, source_id, source_type, content_hash, conn=conn)
            offset += n

    logger.info(
        "Apple Notes: %d processed, %d unchanged (skipped)",
        len(notes) - skipped_notes,
        skipped_notes,
    )
    logger.info(
        "Word docs: %d processed, %d unchanged (skipped)",
        len(docs) - skipped_docs,
        skipped_docs,
    )
    logger.info("Sync complete. %d documents processed.", len(pending))
    return 0


def cmd_chat(args: argparse.Namespace) -> int:
    """Placeholder — real chat is via Streamlit."""
    print("Run `streamlit run app.py` for the full chat UI.")
    print("Or use the Streamlit app directly in your browser.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mh-mind")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("sync", help="Ingest Apple Notes and Word docs into the local corpus.")
    sub.add_parser("chat", help="Chat with your notes in the terminal.")

    args = parser.parse_args(argv)
    handlers = {"sync": cmd_sync, "chat": cmd_chat}
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
