"""Auto-save chat transcripts as Markdown files."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from mh_mind.chat import ChatResponse
from mh_mind.config import ARTIFACTS_DIR


def _slugify(text: str, max_len: int = 40) -> str:
    """Turn a topic string into a filesystem-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:max_len]


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split a Markdown file into frontmatter dict and body text."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            meta = {}
            for line in parts[1].strip().splitlines():
                if ": " in line:
                    key, value = line.split(": ", 1)
                    meta[key.strip()] = value.strip()
            return meta, parts[2]
    return {}, text


def _extract_session_id(filename: str) -> str | None:
    """Extract session_id from filename like '2026-04-18_a1b2c3d4_topic.md'."""
    parts = filename.split("_", 2)
    if len(parts) >= 3:
        return parts[1]
    return None


def list_artifacts(exclude_session_id: str | None = None) -> list[dict]:
    """List all saved artifact files, newest first.

    Returns a list of dicts with keys: path, date, topic, session_id.
    """
    if not ARTIFACTS_DIR.exists():
        return []

    artifacts = []
    for filepath in ARTIFACTS_DIR.glob("*.md"):
        text = filepath.read_text(encoding="utf-8")
        meta, _ = _parse_frontmatter(text)
        session_id = _extract_session_id(filepath.stem)

        if exclude_session_id and session_id == exclude_session_id:
            continue

        artifacts.append({
            "path": filepath,
            "date": meta.get("date", ""),
            "topic": meta.get("topic", filepath.stem),
            "session_id": session_id,
        })

    artifacts.sort(key=lambda a: a["path"].name, reverse=True)
    return artifacts


def parse_artifact(filepath: Path) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """Parse an artifact file into metadata and conversation turns.

    Returns:
        (metadata_dict, [(user_query, assistant_answer), ...])
    """
    text = filepath.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)

    turns: list[tuple[str, str]] = []
    current_role = None
    current_lines: list[str] = []

    user_query = ""

    for line in body.splitlines():
        if line.strip() == "## User":
            # Save previous assistant block if any
            if current_role == "assistant" and user_query:
                turns.append((user_query, "\n".join(current_lines).strip()))
            current_role = "user"
            current_lines = []
        elif line.strip() == "## Assistant":
            if current_role == "user":
                user_query = "\n".join(current_lines).strip()
            current_role = "assistant"
            current_lines = []
        elif line.strip().startswith("### Sources") and current_role == "assistant":
            # Stop collecting assistant content before sources section
            current_role = "sources"
        elif line.strip() == "---" and current_role in ("assistant", "sources"):
            # Artifact turn separator — save the turn
            if user_query:
                turns.append((user_query, "\n".join(current_lines).strip()))
                user_query = ""
            current_role = None
            current_lines = []
        else:
            if current_role in ("user", "assistant"):
                current_lines.append(line)

    # Capture final turn if file doesn't end with ---
    if current_role == "assistant" and user_query:
        turns.append((user_query, "\n".join(current_lines).strip()))

    return meta, turns


def save_transcript(
    transcript: list[tuple[str, ChatResponse]],
    topic: str,
    scope: str = "both",
    session_id: str | None = None,
) -> Path:
    """Save a chat transcript as a Markdown file.

    Args:
        transcript: List of (user_query, ChatResponse) pairs.
        topic: Short topic string (used in the filename).
        scope: The search scope used during the session.
        session_id: If provided, creates a deterministic filename per session
                    (overwrites on each turn instead of creating new files).

    Returns:
        Path to the saved artifact file.
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = _slugify(topic) if topic else "chat"

    if session_id:
        # Deterministic filename — same session overwrites the same file
        filename = f"{date_str}_{session_id}_{slug}.md"
    else:
        filename = f"{date_str}_{slug}.md"

    filepath = ARTIFACTS_DIR / filename

    # Collect all unique source IDs for frontmatter
    all_source_ids = set()
    for _, response in transcript:
        for src in response.sources:
            all_source_ids.add(src.source_id)

    # Build the file
    lines = [
        "---",
        f"date: {date_str}",
        f"scope: {scope}",
        f"topic: {topic}",
        f"sources_referenced: {len(all_source_ids)}",
        "---",
        "",
    ]

    for user_query, response in transcript:
        lines.append(f"## User")
        lines.append("")
        lines.append(user_query)
        lines.append("")
        lines.append(f"## Assistant")
        lines.append("")
        lines.append(response.answer)
        lines.append("")

        if response.sources:
            lines.append("### Sources")
            lines.append("")
            for src in response.sources:
                title = src.metadata.get("title", "Untitled")
                date = src.metadata.get("created", src.metadata.get("modified", ""))
                source_type = "Apple Note" if src.source == "notes" else "Word doc"
                excerpt = src.text[:200].replace("\n", " ")
                lines.append(f"- **[{src.number}]** {source_type}: \"{title}\" ({date})")
                lines.append(f"  > {excerpt}...")
                lines.append("")

        lines.append("---")
        lines.append("")

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath
