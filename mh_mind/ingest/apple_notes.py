"""Ingest Apple Notes via AppleScript export.

Exports all notes from Notes.app as Markdown files with YAML frontmatter,
then reads them back into AppleNote dataclasses.
"""

import hashlib
import logging
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

import yaml

from mh_mind.config import NOTES_EXPORT_DIR

logger = logging.getLogger(__name__)

APPLESCRIPT_PATH = Path(__file__).parent / "export_notes.applescript"


@dataclass
class AppleNote:
    id: str
    title: str
    body: str  # plain text (HTML stripped)
    folder: str
    created: datetime
    modified: datetime
    source_path: Path  # path to the exported .md file


class _HTMLTextExtractor(HTMLParser):
    """Minimal HTML-to-plain-text converter using stdlib only."""

    def __init__(self):
        super().__init__()
        self._pieces: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("br", "p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"):
            self._pieces.append("\n")
        if tag in ("style", "script"):
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "table"):
            self._pieces.append("\n")
        if tag in ("style", "script"):
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._pieces.append(data)

    def get_text(self) -> str:
        text = "".join(self._pieces)
        # Collapse excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def html_to_text(html: str) -> str:
    """Convert HTML body from Apple Notes to plain text."""
    parser = _HTMLTextExtractor()
    parser.feed(html)
    return parser.get_text()


def _run_applescript(output_dir: Path) -> tuple[int, int]:
    """Run the export AppleScript and return (exported_count, error_count).

    Raises RuntimeError if the AppleScript can't talk to Notes.app
    (e.g. macOS Automation permission denied).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["osascript", str(APPLESCRIPT_PATH), str(output_dir)],
        capture_output=True,
        text=True,
        timeout=300,  # 5 min — generous for large libraries
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "not allowed assistive access" in stderr or "not permitted" in stderr.lower():
            raise RuntimeError(
                "macOS denied Automation access to Notes.app. "
                "Go to System Settings → Privacy & Security → Automation "
                "and enable access for Terminal (or your terminal app)."
            )
        raise RuntimeError(f"AppleScript export failed (exit {result.returncode}): {stderr}")

    # Parse the "exported:N,errors:M" return value
    stdout = result.stdout.strip()
    match = re.match(r"exported:(\d+),errors:(\d+)", stdout)
    if not match:
        logger.warning("Unexpected AppleScript output: %s", stdout)
        return 0, 0

    return int(match.group(1)), int(match.group(2))


def _parse_exported_file(path: Path) -> AppleNote | None:
    """Parse a single exported .md file into an AppleNote."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.warning("Skipping %s: could not decode as UTF-8", path)
        return None

    # Split YAML frontmatter from body
    if not text.startswith("---"):
        logger.warning("Skipping %s: no YAML frontmatter", path)
        return None

    parts = text.split("---", 2)
    if len(parts) < 3:
        logger.warning("Skipping %s: malformed frontmatter", path)
        return None

    try:
        meta = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        logger.warning("Skipping %s: YAML parse error: %s", path, e)
        return None

    if not isinstance(meta, dict):
        logger.warning("Skipping %s: frontmatter is not a mapping", path)
        return None

    html_body = parts[2].strip()
    plain_body = html_to_text(html_body)

    # Parse dates — the AppleScript writes ISO 8601 without timezone
    def parse_dt(val: str | datetime) -> datetime:
        if isinstance(val, datetime):
            return val
        return datetime.fromisoformat(val)

    try:
        return AppleNote(
            id=meta.get("note_id", path.stem),
            title=meta.get("title", "Untitled"),
            body=plain_body,
            folder=meta.get("folder", "Unknown"),
            created=parse_dt(meta["created"]),
            modified=parse_dt(meta["modified"]),
            source_path=path,
        )
    except (KeyError, ValueError) as e:
        logger.warning("Skipping %s: missing or bad metadata: %s", path, e)
        return None


def _content_hash(note: AppleNote) -> str:
    """Hash the note body for change detection."""
    return hashlib.sha256(note.body.encode()).hexdigest()[:16]


def export_notes(
    output_dir: Path = NOTES_EXPORT_DIR,
    force: bool = False,
) -> list[AppleNote]:
    """Export Apple Notes and return parsed AppleNote objects.

    Args:
        output_dir: Where to write the exported .md files.
        force: If True, re-export even if files already exist.

    Returns:
        List of parsed AppleNote dataclasses.
    """
    logger.info("Exporting Apple Notes to %s ...", output_dir)
    exported, errors = _run_applescript(output_dir)
    logger.info("AppleScript finished: %d exported, %d errors", exported, errors)

    # Read all .md files from the export directory
    notes: list[AppleNote] = []
    md_files = sorted(output_dir.rglob("*.md"))

    for path in md_files:
        note = _parse_exported_file(path)
        if note is not None:
            notes.append(note)

    logger.info("Parsed %d notes from %d files", len(notes), len(md_files))
    return notes
