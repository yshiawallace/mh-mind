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
    from mh_mind.chunk import Chunk, chunk_text
    from mh_mind.embed import embed_documents
    from mh_mind.ingest.apple_notes import export_notes
    from mh_mind.ingest.word_docs import load_docs
    from mh_mind.store import (
        get_source_hash,
        init_db,
        update_source_hash,
        upsert_chunks,
    )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    init_db(CORPUS_DB)

    all_chunks: list[Chunk] = []

    # --- Apple Notes ---
    logger.info("Ingesting Apple Notes...")
    try:
        notes = export_notes()
    except RuntimeError as e:
        logger.error("Apple Notes export failed: %s", e)
        notes = []

    skipped_notes = 0
    for note in notes:
        content_hash = hashlib.sha256(note.body.encode()).hexdigest()[:16]
        stored_hash = get_source_hash(CORPUS_DB, note.id)

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
            embeddings = embed_documents([c.text for c in chunks])
            upsert_chunks(CORPUS_DB, chunks, embeddings)
            update_source_hash(CORPUS_DB, note.id, "notes", content_hash)

    logger.info(
        "Apple Notes: %d processed, %d unchanged (skipped)",
        len(notes) - skipped_notes,
        skipped_notes,
    )

    # --- Word Docs ---
    logger.info("Ingesting Word documents...")
    doc_paths = load_docs_paths()
    docs = load_docs(doc_paths) if doc_paths else []

    skipped_docs = 0
    for doc in docs:
        content_hash = hashlib.sha256(doc.body.encode()).hexdigest()[:16]
        source_id = str(doc.path)
        stored_hash = get_source_hash(CORPUS_DB, source_id)

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
            embeddings = embed_documents([c.text for c in chunks])
            upsert_chunks(CORPUS_DB, chunks, embeddings)
            update_source_hash(CORPUS_DB, source_id, "docs", content_hash)

    logger.info(
        "Word docs: %d processed, %d unchanged (skipped)",
        len(docs) - skipped_docs,
        skipped_docs,
    )

    total = (len(notes) - skipped_notes) + (len(docs) - skipped_docs)
    logger.info("Sync complete. %d documents processed.", total)
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
