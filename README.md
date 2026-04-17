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

## Requirements

- macOS (required for Apple Notes export via AppleScript)
- Python 3.11+
- An [OpenRouter](https://openrouter.ai/) API key

## Setup

1. **Clone the repo and install dependencies:**

   ```bash
   git clone <repo-url>
   cd mh-mind
   ```

   With [uv](https://docs.astral.sh/uv/) (recommended):
   ```bash
   uv sync --extra embed
   ```

   Or with pip:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[embed]"
   ```

2. **Add your OpenRouter API key:**

   ```bash
   cp .env.example .env
   ```

   Open `.env` and paste your key:
   ```
   OPENROUTER_API_KEY=sk-or-v1-your-key-here
   ```

3. **Configure Word doc folders** (optional — skip if you only want Apple Notes):

   Create `~/mh-mind/docs_paths.yaml` with a list of folders containing your `.docx` files:

   ```yaml
   - /Users/yourname/Documents/Papers
   - /Users/yourname/Dropbox/Drafts
   ```

4. **Grant Automation access:**

   The first time you run `mh-mind sync`, macOS will prompt you to allow Terminal (or your terminal app) to control Notes.app. Click **Allow**. If you accidentally deny it, go to **System Settings → Privacy & Security → Automation** and enable it there.

## Usage

### Sync your corpus

```bash
mh-mind sync
```

This exports your Apple Notes, parses your Word docs, chunks everything, generates embeddings locally, and stores it all in `~/mh-mind/corpus.db`.

- First run: downloads the embedding model (~500 MB) and processes your entire corpus. This may take a few minutes.
- Subsequent runs: only processes new or changed content (incremental).

### Chat with your notes

```bash
streamlit run app.py
```

Opens the chat UI at [http://localhost:8501](http://localhost:8501). From there you can:

- Ask questions and get answers with inline `[1]` `[2]` citations
- Click any citation to expand the source excerpt
- Toggle the search scope between **Apple Notes**, **Word docs**, or **Both**
- Start a new conversation from the sidebar

Every conversation is auto-saved as a Markdown file in `~/mh-mind/artifacts/`.

## Data layout

Everything the app produces lives under `~/mh-mind/` (outside the repo):

```
~/mh-mind/
├── corpus.db              # chunks + embeddings + metadata
├── notes_export/          # raw AppleScript output
├── docs_paths.yaml        # list of configured Word-doc folders (you create this)
└── artifacts/             # auto-saved chat transcripts
```
