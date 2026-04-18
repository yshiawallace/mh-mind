# mh-mind

A personal app for chatting with your Apple Notes and Word documents.

Your corpus is stored and indexed locally. Chunk text is sent to OpenAI for embedding; only the top-K retrieved chunks for a given query are sent to OpenRouter for generation. The full corpus is never uploaded in bulk.

## Architecture

- **Ingestion** — Apple Notes via AppleScript → Markdown + YAML frontmatter; Word docs via `python-docx` over configured folders.
- **Chunking** — uniform 512-token chunks with 64-token overlap, both sources.
- **Embeddings** — OpenAI `text-embedding-3-large` (3,072-dim).
- **Vector store** — `sqlite-vec` in a single SQLite file at `~/mh-mind/corpus.db`.
- **Retrieval** — vector search with a source-scope filter: `notes` / `docs` / `both`.
- **Generation** — OpenRouter (default `anthropic/claude-sonnet-4-5`) behind a swappable `LLMProvider` interface.
- **UI** — Streamlit, runs locally in your browser, with a creativity level slider and search scope toggle.
- **Artifacts** — every chat session auto-saved as Markdown under `~/mh-mind/artifacts/`.

## Requirements

- macOS (required for Apple Notes export via AppleScript)
- Python 3.11+
- An [OpenAI](https://platform.openai.com/) API key (for embeddings)
- An [OpenRouter](https://openrouter.ai/) API key (for chat generation)

## Setup

1. **Clone the repo and install dependencies:**

   ```bash
   git clone <repo-url>
   cd mh-mind
   ```

   With [uv](https://docs.astral.sh/uv/) (recommended):
   ```bash
   uv sync
   ```

   Or with pip:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

2. **Add your API keys:**

   ```bash
   cp .env.example .env
   ```

   Open `.env` and paste both keys:
   ```
   OPENROUTER_API_KEY=sk-or-v1-your-key-here
   OPENAI_API_KEY=sk-your-openai-key-here
   ```

3. **Configure Word doc folders** (optional — skip if you only want Apple Notes):

   Create the data directory and config file:

   ```bash
   mkdir -p ~/mh-mind
   ```

   Then create `~/mh-mind/docs_paths.yaml` with a list of folders containing your `.docx` files:

   ```yaml
   - /Users/yourname/Documents/Papers
   - /Users/yourname/Dropbox/Drafts
   ```

   Note: this file lives in the `~/mh-mind/` data directory, not in the project repo.

4. **Grant Automation access:**

   The first time you run `mh-mind sync`, macOS will prompt you to allow Terminal (or your terminal app) to control Notes.app. Click **Allow**. If you accidentally deny it, go to **System Settings → Privacy & Security → Automation** and enable it there.

## Usage

If you installed with **uv**, prefix commands with `uv run` (or activate the venv with `source .venv/bin/activate` first).

### Sync your corpus

```bash
uv run mh-mind sync
```

This exports your Apple Notes, parses your Word docs, chunks everything, generates embeddings via OpenAI, and stores it all in `~/mh-mind/corpus.db`.

- First run: processes your entire corpus. This may take a few minutes.
- Subsequent runs: only processes new or changed content (incremental).

### Chat with your notes

```bash
uv run streamlit run app.py
```

Opens the chat UI at [http://localhost:8501](http://localhost:8501). From there you can:

- Ask questions and get answers with inline `[1]` `[2]` citations
- Click any citation to expand the source excerpt
- Toggle the search scope between **Apple Notes**, **Word docs**, or **Both**
- Adjust the **Creativity level** slider (Precise → Balanced → Creative → Adventurous → Wild → Unhinged)
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
