"""CLI entry points: `mh-mind ingest`, `mh-mind embed`, `mh-mind sync`, `mh-mind chat`."""

import argparse
import hashlib
import logging
import sys

from mh_mind.config import (
    CORPUS_DB,
    DATA_DIR,
    DOCS_EXPORT_DIR,
    load_docs_paths,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def cmd_ingest(args: argparse.Namespace) -> int:
    """Parse Apple Notes + Word docs, chunk, and store (no embedding API calls)."""
    from mh_mind.chunk import chunk_text
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

        exported_docs = 0
        for doc in docs:
            content_hash = hashlib.sha256(doc.body.encode()).hexdigest()[:16]
            source_id = str(doc.path)
            stored_hash = get_source_hash(CORPUS_DB, source_id, conn=conn)

            if stored_hash == content_hash:
                skipped_docs += 1
                continue

            # Write parsed text to disk for inspection
            DOCS_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            export_path = DOCS_EXPORT_DIR / f"{doc.title}.txt"
            export_path.write_text(doc.body, encoding="utf-8")
            exported_docs += 1

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

        # Store chunks WITHOUT embeddings
        for chunks, source_id, source_type, content_hash in pending:
            upsert_chunks(CORPUS_DB, chunks, conn=conn)
            update_source_hash(CORPUS_DB, source_id, source_type, content_hash, conn=conn)

    logger.info(
        "Apple Notes: %d processed, %d unchanged (skipped)",
        len(notes) - skipped_notes,
        skipped_notes,
    )
    logger.info(
        "Word docs: %d processed, %d unchanged (skipped), %d exported to %s",
        len(docs) - skipped_docs,
        skipped_docs,
        exported_docs,
        DOCS_EXPORT_DIR,
    )

    total_chunks = sum(len(chunks) for chunks, _, _, _ in pending)
    logger.info("Ingest complete. %d documents processed, %d chunks stored.", len(pending), total_chunks)
    logger.info("Run `mh-mind embed` to generate embeddings for new chunks.")
    return 0


def cmd_embed(args: argparse.Namespace) -> int:
    """Generate embeddings for any chunks that don't have them yet."""
    from mh_mind.embed import embed_documents
    from mh_mind.store import (
        connect,
        get_unembedded_chunks,
        init_db,
        store_embeddings,
    )

    init_db(CORPUS_DB)

    with connect(CORPUS_DB) as conn:
        unembedded = get_unembedded_chunks(CORPUS_DB, conn=conn)

        if not unembedded:
            logger.info("All chunks already have embeddings. Nothing to do.")
            return 0

        logger.info("Found %d chunks without embeddings. Calling OpenAI API...", len(unembedded))

        chunk_ids = [c["id"] for c in unembedded]
        texts = [c["text"] for c in unembedded]
        embeddings = embed_documents(texts)

        store_embeddings(CORPUS_DB, chunk_ids, embeddings, conn=conn)

    logger.info("Embed complete. %d chunks embedded.", len(unembedded))
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    """Ingest + embed in one step (convenience command)."""
    result = cmd_ingest(args)
    if result != 0:
        return result
    return cmd_embed(args)


def cmd_chat(args: argparse.Namespace) -> int:
    """Placeholder — real chat is via Streamlit."""
    print("Run `streamlit run app.py` for the full chat UI.")
    print("Or use the Streamlit app directly in your browser.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mh-mind")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ingest", help="Parse and chunk documents (no API calls).")
    sub.add_parser("embed", help="Generate embeddings for unembedded chunks.")
    sub.add_parser("sync", help="Ingest + embed in one step.")
    sub.add_parser("chat", help="Chat with your notes in the terminal.")

    args = parser.parse_args(argv)
    handlers = {
        "ingest": cmd_ingest,
        "embed": cmd_embed,
        "sync": cmd_sync,
        "chat": cmd_chat,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
