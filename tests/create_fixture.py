"""Create a test fixture .docx file with footnotes and endnotes.

Run this script to generate (or regenerate) the fixture:

    python tests/create_fixture.py

The fixture contains:
    - Paragraph 1: body text + footnote 2
    - Paragraph 2: body text + footnote 3 + endnote 2
    - Paragraph 3: body text with no notes
"""

import zipfile
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent / "fixtures"
OUTPUT_PATH = FIXTURE_DIR / "sample_with_footnotes.docx"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
PKG_RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

# --- XML templates ---

CONTENT_TYPES = f"""\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="{CT_NS}">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/footnotes.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/>
  <Override PartName="/word/endnotes.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.endnotes+xml"/>
</Types>"""

PKG_RELS = f"""\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{PKG_RELS_NS}">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
    Target="word/document.xml"/>
</Relationships>"""

DOC_RELS = f"""\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{PKG_RELS_NS}">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes"
    Target="footnotes.xml"/>
  <Relationship Id="rId2"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/endnotes"
    Target="endnotes.xml"/>
</Relationships>"""

# Body text with footnote/endnote references embedded in the runs.
# Paragraph 1: text + footnote ref id=2
# Paragraph 2: text + footnote ref id=3 + endnote ref id=2
# Paragraph 3: text with no notes
DOCUMENT_XML = f"""\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{W_NS}" xmlns:r="{R_NS}">
  <w:body>
    <w:p>
      <w:r><w:t xml:space="preserve">The court established the precedent in Smith v Jones</w:t></w:r>
      <w:r>
        <w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr>
        <w:footnoteReference w:id="2"/>
      </w:r>
      <w:r><w:t xml:space="preserve"> which became binding authority.</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t xml:space="preserve">This was later affirmed by the appellate court</w:t></w:r>
      <w:r>
        <w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr>
        <w:footnoteReference w:id="3"/>
      </w:r>
      <w:r><w:t xml:space="preserve"> and discussed extensively in the literature</w:t></w:r>
      <w:r>
        <w:rPr><w:rStyle w:val="EndnoteReference"/></w:rPr>
        <w:endnoteReference w:id="2"/>
      </w:r>
      <w:r><w:t xml:space="preserve"> by subsequent commentators.</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>The doctrine remains controversial in several jurisdictions.</w:t></w:r>
    </w:p>
  </w:body>
</w:document>"""

FOOTNOTES_XML = f"""\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:footnotes xmlns:w="{W_NS}">
  <w:footnote w:type="separator" w:id="0">
    <w:p><w:r><w:separator/></w:r></w:p>
  </w:footnote>
  <w:footnote w:type="continuationSeparator" w:id="1">
    <w:p><w:r><w:continuationSeparator/></w:r></w:p>
  </w:footnote>
  <w:footnote w:id="2">
    <w:p>
      <w:r><w:t xml:space="preserve">Smith v Jones [2018] UKSC 15, para 42.</w:t></w:r>
    </w:p>
  </w:footnote>
  <w:footnote w:id="3">
    <w:p>
      <w:r><w:t xml:space="preserve">Davies, M. (2020). Administrative Law. Hart Publishing, p.112.</w:t></w:r>
    </w:p>
  </w:footnote>
</w:footnotes>"""

ENDNOTES_XML = f"""\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:endnotes xmlns:w="{W_NS}">
  <w:endnote w:type="separator" w:id="0">
    <w:p><w:r><w:separator/></w:r></w:p>
  </w:endnote>
  <w:endnote w:type="continuationSeparator" w:id="1">
    <w:p><w:r><w:continuationSeparator/></w:r></w:p>
  </w:endnote>
  <w:endnote w:id="2">
    <w:p>
      <w:r><w:t xml:space="preserve">See also Chen v Republic [2019] SGCA 8, at [15]-[20].</w:t></w:r>
    </w:p>
  </w:endnote>
</w:endnotes>"""


def main():
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(OUTPUT_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("_rels/.rels", PKG_RELS)
        zf.writestr("word/document.xml", DOCUMENT_XML)
        zf.writestr("word/_rels/document.xml.rels", DOC_RELS)
        zf.writestr("word/footnotes.xml", FOOTNOTES_XML)
        zf.writestr("word/endnotes.xml", ENDNOTES_XML)

    print(f"Created fixture: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
