# mh-mind

A personal app for chatting with your Apple Notes and Word documents.

Your corpus is stored and indexed locally. Only the top-K retrieved chunks for a given query are sent to an LLM provider (OpenRouter by default). The full corpus never leaves your machine.

## Architecture

- **Ingestion** — Apple Notes via AppleScript → Markdown + YAML frontmatter; Word docs via `python-docx` over configured folders.
- **Chunking** — uniform 512-token chunks with 64-token overlap, both sources.
- **Embeddings** — local `nomic-ai/nomic-embed-text-v1.5` via `sentence-transformers`.
- **Vector store** — `sqlite-vec` in a single SQLite file at `~/mh-mind/corpus.db`.
- **Retrieval** — vector search with a source-scope filter: `notes` / `docs` / `both`.
- **Generation** — OpenRouter (default `anthropic/claude-sonnet-4-5`) behind a swappable `LLMProvider` interface.
- **UI** — Streamlit, runs locally in your browser.
- **Artifacts** — every chat session auto-saved as Markdown under `~/mh-mind/artifacts/`.

## Setup

Requires Python 3.11+.

```bash
cp .env.example .env
# edit .env and paste your OpenRouter API key

python -m venv .venv
source .venv/bin/activate
pip install -e .
```

On first run, macOS will prompt to grant Terminal (or your IDE) **Automation** access to the Notes app. This is required for the AppleScript exporter.

## Usage

```bash
mh-mind sync               # pull Apple Notes + Word docs into the local corpus
streamlit run app.py       # open the chat UI at http://localhost:8501
```

## Data layout

Everything the app produces lives under `~/mh-mind/` (outside the repo):

```
~/mh-mind/
├── corpus.db              # chunks + embeddings + metadata
├── notes_export/          # raw AppleScript output
├── docs_paths.yaml        # list of configured Word-doc folders
└── artifacts/             # auto-saved chat transcripts
```

