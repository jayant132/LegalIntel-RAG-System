"""DOCX parser: recover clause structure from numbering and keep tables in place.

Word files from legal teams rarely use real heading styles, so section headings such as
``3. Gifts and hospitality`` are recognised by their numbering. Each section becomes one
block (heading + its clauses). A hard page break ends a section, because it often separates
two different documents in one file (e.g. an agreement and a later letter of variation).
"""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.document import Document as DocxDocument
from docx.table import Table
from docx.text.paragraph import Paragraph

from legalrag.ingestion.manifest import DocumentRecord
from legalrag.ingestion.models import Block, BlockKind, ParsedDocument
from legalrag.ingestion.parsers._common import clean_multiline, to_markdown_table

_HEADING = re.compile(r"^\d+\.\s+\S")
_MAX_HEADING_LEN = 90
_MAX_CAPTION_LEN = 60

# Constructs python-docx silently skips. If present, text would be lost without any error,
# so we refuse the file and ask for a human to look at it.
_UNSUPPORTED: dict[str, str] = {
    ".//w:ins": "tracked insertion",
    ".//w:del": "tracked deletion",
    ".//w:moveFrom": "tracked move",
    ".//w:moveTo": "tracked move",
    ".//w:commentReference": "comment",
    ".//w:footnoteReference": "footnote",
    ".//w:endnoteReference": "endnote",
    ".//w:sdt": "content control",
    ".//w:txbxContent": "text box",
    ".//w:tc//w:tbl": "nested table",
}
_HARD_BREAK = "./w:r/w:br[@w:type='page'] | ./w:pPr/w:pageBreakBefore | ./w:pPr/w:sectPr"


def _is_heading(text: str) -> bool:
    return (
        bool(_HEADING.match(text))
        and len(text) <= _MAX_HEADING_LEN
        and not text.endswith((".", ";", ":", ","))
    )


def _is_caption(text: str) -> bool:
    """A short unnumbered line without sentence punctuation, e.g. 'Version history'."""
    return (
        len(text) <= _MAX_CAPTION_LEN
        and not text[0].isdigit()
        and not text.endswith((".", ";", ":", ","))
    )


def _reject_unsupported(doc: DocxDocument, path: Path) -> None:
    body = doc.element.body
    for xpath, what in _UNSUPPORTED.items():
        if body.xpath(xpath):
            raise ValueError(f"{path.name}: contains a {what}; review before ingesting")


def _table_rows(table: Table) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.rows:
        cells: list[str] = []
        previous = None
        for cell in row.cells:
            # python-docx repeats a horizontally merged cell once per grid column.
            if previous is not None and cell._tc is previous:
                continue
            previous = cell._tc
            cells.append(cell.text)
        rows.append(cells)
    return rows


def parse_docx(record: DocumentRecord, path: Path) -> ParsedDocument:
    """One TEXT block per section (heading + clauses) and one TABLE block per table."""
    doc = Document(str(path))
    _reject_unsupported(doc, path)

    blocks: list[Block] = []
    heading = ""
    lines: list[str] = []
    heading_used = False

    def flush() -> None:
        nonlocal heading_used
        if lines:
            text = "\n".join([heading, *lines] if heading else lines)
            blocks.append(Block(kind=BlockKind.TEXT, text=text))
            lines.clear()
            heading_used = True

    def close_section() -> None:
        nonlocal heading_used
        flush()
        if heading and not heading_used:  # a heading with nothing under it must not vanish
            blocks.append(Block(kind=BlockKind.TEXT, text=heading))
        heading_used = False

    for item in doc.iter_inner_content():
        if isinstance(item, Table):
            caption = lines.pop() if lines and _is_caption(lines[-1]) else ""
            flush()
            md = to_markdown_table(_table_rows(item))
            if md:
                head = "\n".join(part for part in (heading, caption) if part)
                blocks.append(Block(kind=BlockKind.TABLE, text=f"{head}\n\n{md}" if head else md))
                heading_used = True
            continue
        paragraph: Paragraph = item
        if paragraph._p.xpath(_HARD_BREAK):
            close_section()
            heading = ""
        text = clean_multiline(paragraph.text)
        if not text:
            continue
        if _is_heading(text):
            close_section()
            heading = text
        else:
            lines.append(text)
    close_section()
    return ParsedDocument(doc_id=record.doc_id, blocks=tuple(blocks))
