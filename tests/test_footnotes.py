"""Tests for mh_mind.ingest.footnotes."""

import logging
from pathlib import Path

import pytest
from lxml import etree

from mh_mind.ingest.footnotes import paragraph_text_with_notes, parse_notes

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_with_footnotes.docx"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


# --- Helpers ---


def _get_paragraphs_from_fixture():
    """Read the fixture docx and return the <w:p> elements from document.xml."""
    import zipfile

    with zipfile.ZipFile(FIXTURE_PATH, "r") as zf:
        doc_xml = zf.read("word/document.xml")

    root = etree.fromstring(doc_xml)
    return root.findall(f".//{{{W_NS}}}p")


# --- parse_notes tests ---


class TestParseNotes:
    def test_extracts_footnotes(self):
        notes = parse_notes(FIXTURE_PATH)
        assert "fn:2" in notes
        assert "fn:3" in notes
        assert "Smith v Jones" in notes["fn:2"]
        assert "Davies" in notes["fn:3"]

    def test_extracts_endnotes(self):
        notes = parse_notes(FIXTURE_PATH)
        assert "en:2" in notes
        assert "Chen v Republic" in notes["en:2"]

    def test_skips_separator_ids(self):
        notes = parse_notes(FIXTURE_PATH)
        # IDs 0 and 1 are separators — they should not appear
        for key in notes:
            _, note_id = key.split(":")
            assert note_id not in ("0", "1")

    def test_no_footnotes_returns_empty(self, tmp_path):
        """A docx with no footnotes.xml should return an empty dict."""
        import zipfile

        # Create a minimal .docx with no footnotes or endnotes parts
        minimal_docx = tmp_path / "no_notes.docx"
        with zipfile.ZipFile(minimal_docx, "w") as zf:
            zf.writestr(
                "word/document.xml",
                f'<?xml version="1.0"?>'
                f'<w:document xmlns:w="{W_NS}">'
                f"<w:body><w:p><w:r><w:t>Hello</w:t></w:r></w:p></w:body>"
                f"</w:document>",
            )

        notes = parse_notes(minimal_docx)
        assert notes == {}


# --- paragraph_text_with_notes tests ---


class TestParagraphTextWithNotes:
    @pytest.fixture()
    def notes(self):
        return parse_notes(FIXTURE_PATH)

    @pytest.fixture()
    def paragraphs(self):
        return _get_paragraphs_from_fixture()

    def test_inlines_footnote(self, paragraphs, notes):
        """Paragraph 1 references footnote 2 — it should appear in the output."""
        text = paragraph_text_with_notes(paragraphs[0], notes)
        assert "The court established" in text
        assert "[Footnote 2]: Smith v Jones [2018] UKSC 15, para 42." in text

    def test_inlines_footnote_and_endnote(self, paragraphs, notes):
        """Paragraph 2 references footnote 3 and endnote 2."""
        text = paragraph_text_with_notes(paragraphs[1], notes)
        assert "later affirmed" in text
        assert "[Footnote 3]: Davies" in text
        assert "[Endnote 2]: See also Chen v Republic" in text

    def test_no_notes_paragraph(self, paragraphs, notes):
        """Paragraph 3 has no note references — just plain text."""
        text = paragraph_text_with_notes(paragraphs[2], notes)
        assert "controversial" in text
        assert "[Footnote" not in text
        assert "[Endnote" not in text

    def test_missing_note_id_logs_warning(self, paragraphs, caplog):
        """If a referenced note ID is not in the dict, log a warning and skip."""
        empty_notes: dict[str, str] = {}
        with caplog.at_level(logging.WARNING):
            text = paragraph_text_with_notes(paragraphs[0], empty_notes)

        # Should still have the paragraph text
        assert "The court established" in text
        # Should not have a [Footnote] line (the note was missing)
        assert "[Footnote" not in text
        # Should have logged a warning
        assert "not in parsed notes" in caplog.text

    def test_empty_paragraph(self, notes):
        """An empty paragraph element should return an empty string."""
        empty_para = etree.fromstring(f'<w:p xmlns:w="{W_NS}"></w:p>')
        text = paragraph_text_with_notes(empty_para, notes)
        assert text == ""
