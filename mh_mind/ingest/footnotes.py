"""Parse and inline footnotes/endnotes from Word (.docx) documents.

Opens the .docx as a ZIP archive to read word/footnotes.xml and
word/endnotes.xml directly, since python-docx has no high-level
footnote API.
"""

import logging
import zipfile
from pathlib import Path

from lxml import etree

logger = logging.getLogger(__name__)

# Word XML namespace
_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_W = f"{{{_W_NS}}}"

# Footnote/endnote IDs 0 and 1 are special (separator, continuationSeparator)
_SKIP_IDS = {"0", "1"}


def _parse_notes_xml(xml_bytes: bytes, tag_name: str, prefix: str) -> dict[str, str]:
    """Parse a footnotes.xml or endnotes.xml file into a dict.

    Args:
        xml_bytes: Raw XML content of the file.
        tag_name: "footnote" or "endnote".
        prefix: "fn" or "en" — prepended to the ID in the dict key.

    Returns:
        Dict mapping "{prefix}:{id}" to the note's plain text.
    """
    root = etree.fromstring(xml_bytes)
    notes: dict[str, str] = {}

    for note_el in root.findall(f"{_W}{tag_name}"):
        # Try namespace-qualified w:id first, fall back to plain id.
        # Real Word documents vary in whether the attribute is qualified.
        note_id = note_el.get(f"{_W}id") or note_el.get("id")
        if note_id is None or note_id in _SKIP_IDS:
            continue

        # Extract all text from <w:t> descendants
        text_parts = []
        for t_el in note_el.iter(f"{_W}t"):
            if t_el.text:
                text_parts.append(t_el.text)

        text = "".join(text_parts).strip()
        if text:
            notes[f"{prefix}:{note_id}"] = text
            logger.debug("  %s:%s = %s", prefix, note_id, text[:80])

    return notes


def parse_notes(docx_path: Path) -> dict[str, str]:
    """Parse footnotes and endnotes from a .docx file.

    Opens the .docx as a ZIP and reads word/footnotes.xml and
    word/endnotes.xml. Returns a dict mapping prefixed ID strings
    to their plain text content.

    Keys are prefixed: "fn:2" for footnote id=2, "en:3" for endnote id=3.
    Special separator notes (IDs "0" and "1") are skipped.
    Returns an empty dict if no footnotes or endnotes exist.
    """
    notes: dict[str, str] = {}

    with zipfile.ZipFile(docx_path, "r") as zf:
        file_list = zf.namelist()

        if "word/footnotes.xml" in file_list:
            xml_bytes = zf.read("word/footnotes.xml")
            fn_notes = _parse_notes_xml(xml_bytes, "footnote", "fn")
            notes.update(fn_notes)
            logger.debug(
                "Parsed %d footnotes from %s", len(fn_notes), docx_path.name
            )

        if "word/endnotes.xml" in file_list:
            xml_bytes = zf.read("word/endnotes.xml")
            en_notes = _parse_notes_xml(xml_bytes, "endnote", "en")
            notes.update(en_notes)
            logger.debug(
                "Parsed %d endnotes from %s", len(en_notes), docx_path.name
            )

    return notes


def _collect_runs(element, notes, text_parts, referenced_notes):
    """Walk an element's children to collect text and note references.

    Handles <w:r> (runs) and <w:hyperlink> (which contain runs).
    Skips <w:pPr> (paragraph properties) and other non-content elements.

    Args:
        element: An lxml element to walk (paragraph or hyperlink).
        notes: The notes dict (used only for validation logging).
        text_parts: List to append text strings to (mutated in place).
        referenced_notes: List to append (prefix, id, label) tuples to.
    """
    for child in element:
        tag = child.tag

        if tag == f"{_W}r":
            # A run — extract text and check for note references
            for run_child in child:
                if run_child.tag == f"{_W}t" and run_child.text:
                    text_parts.append(run_child.text)
                elif run_child.tag == f"{_W}footnoteReference":
                    note_id = run_child.get(f"{_W}id") or run_child.get("id")
                    if note_id and note_id not in _SKIP_IDS:
                        referenced_notes.append(("fn", note_id, "Footnote"))
                elif run_child.tag == f"{_W}endnoteReference":
                    note_id = run_child.get(f"{_W}id") or run_child.get("id")
                    if note_id and note_id not in _SKIP_IDS:
                        referenced_notes.append(("en", note_id, "Endnote"))

        elif tag == f"{_W}hyperlink":
            # Hyperlinks contain runs — recurse into them
            _collect_runs(child, notes, text_parts, referenced_notes)


def paragraph_text_with_notes(para_element, notes: dict[str, str]) -> str:
    """Extract text from a paragraph element, inlining referenced notes.

    Walks the paragraph's XML children to collect text and find
    footnote/endnote references. Referenced notes are appended after
    the paragraph text as:
        [Footnote N]: <note text>
    or:
        [Endnote N]: <note text>

    Args:
        para_element: An lxml element for a <w:p> paragraph.
        notes: Dict from parse_notes() mapping prefixed IDs to text.

    Returns:
        The paragraph text with any referenced notes appended on new lines.
        If the paragraph has no text, returns an empty string.
    """
    text_parts: list[str] = []
    referenced_notes: list[tuple[str, str, str]] = []  # (prefix, id, label)

    _collect_runs(para_element, notes, text_parts, referenced_notes)

    para_text = "".join(text_parts).strip()
    if not para_text:
        return ""

    if not referenced_notes:
        return para_text

    # Append note lines after the paragraph text
    lines = [para_text]
    for prefix, note_id, label in referenced_notes:
        key = f"{prefix}:{note_id}"
        if key in notes:
            lines.append(f"[{label} {note_id}]: {notes[key]}")
            logger.debug("Inlined %s:%s into paragraph", prefix, note_id)
        else:
            logger.warning(
                "Note reference %s:%s found in paragraph but not in parsed notes — skipping",
                prefix,
                note_id,
            )

    return "\n".join(lines)
