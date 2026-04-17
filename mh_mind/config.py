from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path.home() / "mh-mind"
CORPUS_DB = DATA_DIR / "corpus.db"
NOTES_EXPORT_DIR = DATA_DIR / "notes_export"
DOCS_PATHS_CONFIG = DATA_DIR / "docs_paths.yaml"
ARTIFACTS_DIR = DATA_DIR / "artifacts"

EMBEDDING_MODEL = "nomic-ai/nomic-embed-text-v1.5"
CHUNK_SIZE_TOKENS = 512
CHUNK_OVERLAP_TOKENS = 64

DEFAULT_LLM_MODEL = "anthropic/claude-sonnet-4-5"
