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

# Retrieval Tuning Experiments

This section documents what we've learned about how retrieval works and a set of
experiments to tune it for academic legal writing. Each experiment should be run
in isolation so we can feel the impact of each change independently.

## How retrieval works (summary)

1. **Sync phase (one-time per document):** Each document is split into chunks of
   ~512 tokens (~380 words) with 64 tokens of overlap. Each chunk is sent to
   OpenAI's embedding API (`text-embedding-3-large`) and comes back as a vector
   of 3,072 numbers — a mathematical fingerprint of the chunk's meaning. The
   vectors are stored in `corpus.db` alongside the chunk text.

2. **Chat phase (every question):** Your question is sent to the same OpenAI
   embedding API to get its own vector. That vector is compared against all
   stored chunk vectors locally in SQLite (using sqlite-vec). The top 10 closest
   chunks are returned. Those chunks plus your question are then sent to
   OpenRouter (Claude Sonnet) for generation.

3. **Scope filtering** happens after the similarity search, not before, because
   sqlite-vec doesn't support pre-filtering. The code compensates by
   overfetching and discarding non-matching chunks. The final results are the
   same as pre-filtering; it's just less efficient.

4. **Citations** currently point back to your own notes/documents (e.g. [1] =
   excerpt 1), not to the scholarly sources cited within those documents. This
   is because the system prompt asks the LLM to cite by excerpt number.

## Known issue: footnotes are lost during chunking

Word documents store footnotes separately from body text in the `.docx` format.
When the text is extracted and chunked, footnote content ends up far from the
body text that references it. A chunk might contain "...as Merleau-Ponty
argues⁷..." but the actual footnote 7 with the full citation lives in a
completely different chunk (or may not be retrieved at all).

The fix is to resolve footnotes into the body text during ingestion — before
chunking — so that each footnote's content travels with the passage that
references it.

## Experiment 1: Resolve footnotes during ingestion

**What to change:** Modify Word doc ingestion (`mh_mind/ingest/word_docs.py`) to
parse footnotes from the `.docx` structure and inline them at the point of
reference in the body text, before the text is passed to the chunker.

**What to expect:** Chunks that reference sources will now contain the full
citation text. The LLM will be able to name specific authors, titles, and page
numbers from your footnotes. Chunks will be slightly longer (footnote text is
added to body text), but the semantic content will be richer.

**How to test:** After re-syncing, ask a question you know involves a specific
footnoted source. Compare the answer (and whether it names the source) to the
current behaviour.

**System prompt change:** Once footnotes are in the chunk text, update the system
prompt in `mh_mind/chat.py` to tell the LLM to surface scholarly sources found
within excerpts, distinguishing them from excerpt numbers.

## Experiment 2: Increase chunk size

**What to change:** In `mh_mind/config.py`, increase `CHUNK_SIZE_TOKENS` from
512 to 1024 (~750 words, roughly two pages).

**What to expect:** Each chunk captures more of a sustained argument. For
academic legal writing where complex ideas take several paragraphs to develop,
this means the retrieved context is more coherent and complete. The trade-off:
matching becomes less precise because each chunk's embedding is an average over
more ideas, and you fit fewer total chunks in the LLM's context.

**How to test:** Re-sync the corpus, then ask the same questions you've been
using. Pay attention to whether answers feel more contextually rich or whether
they start including irrelevant material.

## Experiment 3: Increase chunk overlap

**What to change:** In `mh_mind/config.py`, increase `CHUNK_OVERLAP_TOKENS` from
64 to 128 (or 192).

**What to expect:** Ideas that sit at the boundary between two chunks will be
more fully represented in both. This is especially useful for legal reasoning
that builds across paragraphs — a conclusion in one paragraph may depend on a
premise in the previous one, and more overlap means both are more likely to
appear together in a single chunk. The trade-off: more total chunks per document
(slightly more storage and embedding cost during sync), but retrieval quality at
chunk boundaries improves.

**How to test:** Re-sync and ask questions where you know the relevant argument
spans what would be a chunk boundary. Compare whether the answer captures the
full reasoning or cuts off mid-thought.

## Experiment 4: Increase top_k (number of retrieved chunks)

**What to change:** In `mh_mind/chat.py`, increase the `top_k` default from 10
to 15 or 20.

**What to expect:** The LLM gets more material to work with, increasing the
chance that all relevant passages are included. This pairs well with larger chunk
sizes (experiment 2) — if each chunk is bigger and less precisely matched, having
more of them compensates. The trade-off: more text sent to OpenRouter per
question (higher cost), and if too many chunks are loosely relevant, the LLM may
struggle to synthesise or may include irrelevant material.

**How to test:** No re-sync needed — this only affects the chat phase. Ask broad
questions that span multiple documents and see if the answer draws on more
sources. Also check whether the answer gets unfocused.

## Experiment 5: Semantic chunking

**What to change:** Replace the fixed-size chunker in `mh_mind/chunk.py` with
one that splits on structural boundaries — paragraph breaks, section headings,
numbered clauses — and only breaks further if a section exceeds a maximum size.

**What to expect:** Each chunk corresponds to a natural unit of argument rather
than an arbitrary 512-token slice. Legal documents with numbered sections and
clear paragraph structure would benefit most. The trade-off: chunks vary in size
(some short, some long), and the implementation is more involved than changing a
config value.

**How to test:** Re-sync, then compare retrieval quality on the same questions.
Chunks should feel like coherent passages rather than text that starts or ends
mid-sentence.

## Recommended experiment order

1. **Experiment 1 (footnotes)** — fixes a real data loss problem; independent of
   all other changes
2. **Experiment 4 (top_k)** — no re-sync needed, fastest to try and revert
3. **Experiment 2 (chunk size)** — requires re-sync but is a single config change
4. **Experiment 3 (overlap)** — requires re-sync, best tested after you've
   settled on a chunk size
5. **Experiment 5 (semantic chunking)** — most involved, best saved for last
   after you understand the impact of the simpler changes

For each experiment, keep a few benchmark questions that you always ask, so you
can compare answers across runs.
