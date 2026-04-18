"""Auto-save chat transcripts as Markdown files."""

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
