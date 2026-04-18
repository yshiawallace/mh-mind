import logging
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATA_DIR = Path.home() / "mh-mind"
CORPUS_DB = DATA_DIR / "corpus.db"
NOTES_EXPORT_DIR = DATA_DIR / "notes_export"
DOCS_PATHS_CONFIG = DATA_DIR / "docs_paths.yaml"
ARTIFACTS_DIR = DATA_DIR / "artifacts"

EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIM = 3072
CHUNK_SIZE_TOKENS = 512
CHUNK_OVERLAP_TOKENS = 64

DEFAULT_LLM_MODEL = "anthropic/claude-sonnet-4-5"


def load_docs_paths() -> list[Path]:
    """Load the list of Word-doc folder paths from docs_paths.yaml.

    The YAML file should contain a list of directory paths, e.g.:

        - /Users/me/Documents/Papers
        - /Users/me/Dropbox/Drafts

    Returns an empty list (with a warning) if the file doesn't exist.
    """
    if not DOCS_PATHS_CONFIG.exists():
        logger.warning(
            "No docs_paths.yaml found at %s — no Word docs will be ingested. "
            "Create this file with a list of folder paths to enable Word doc ingestion.",
            DOCS_PATHS_CONFIG,
        )
        return []

    with open(DOCS_PATHS_CONFIG) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, list):
        logger.warning("docs_paths.yaml should contain a list of paths, got %s", type(data).__name__)
        return []

    paths = []
    for entry in data:
        p = Path(entry).expanduser()
        if not p.is_dir():
            logger.warning("Skipping non-existent directory: %s", p)
            continue
        paths.append(p)

    return paths
