"""PDF parser for documents that have a text layer.

Fixes what plain text extraction gets wrong in legal PDFs:

* running headers and footers are removed, so they never leak into chunks;
* tables are extracted once, as tables, instead of also appearing as scrambled text;
* wrapped lines are rejoined into paragraphs, using each line's right edge;
* a section that straddles a page break stays together.

Image-only scans have no text layer; they are rejected here and handled by OCR instead.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import pdfplumber
from pdfplumber.page import Page

from legalrag.ingestion.manifest import DocumentRecord
from legalrag.ingestion.models import Block, BlockKind, ParsedDocument
from legalrag.ingestion.parsers._common import to_markdown_table
from legalrag.ingestion.parsers._headings import is_section_heading

_EDGE_LINES = 2  # running headers and footers sit in the first/last lines of a page
_WRAP_TOLERANCE_PT = 60.0  # a wrapped line ends within roughly one word of the right margin
_CAPTION_MAX_LEN = 120

_DIGITS = re.compile(r"\d+")
# A line that begins a new clause even when the previous line was full width.
_CLAUSE_START = re.compile(r"^(?:\d+(?:\.\d+)+[A-Z]?\.?\s|\d+\.\s+[A-Z]|Part [A-Z]\b|\[Footnote)")


@dataclass(frozen=True)
class Line:
    text: str
    x1: float  # right edge in points; used to tell wrapped lines from paragraph ends


@dataclass(frozen=True)
class TextRun:
    """Consecutive lines of body text (may span several pages)."""

    lines: tuple[Line, ...]


@dataclass(frozen=True)
class Grid:
    """One table, cells already cleaned."""

    rows: list[list[str]]


Item = TextRun | Grid


def _mask(line: str) -> str:
    """Replace digits so that 'Page 3' and 'Page 4' compare equal."""
    return _DIGITS.sub("#", line.strip())


def find_page_furniture(pages: Sequence[Sequence[str]]) -> frozenset[str]:
    """Masked edge lines that repeat on (nearly) every page: running headers and footers.

    A line counts only if it sits in the first or last lines of a page, so a repeated
    sentence in the body is never mistaken for furniture. 'Nearly' (all pages but one)
    tolerates a cover page without a header.
    """
    if len(pages) < 2:
        return frozenset()
    seen: Counter[str] = Counter()
    for lines in pages:
        edges = {_mask(x) for x in (*lines[:_EDGE_LINES], *lines[-_EDGE_LINES:]) if x.strip()}
        seen.update(edges)
    needed = max(2, len(pages) - 1)
    return frozenset(line for line, count in seen.items() if count >= needed)


def _lines_between(page: Page, top: float, bottom: float) -> list[Line]:
    if bottom - top < 1:
        return []
    band = page.within_bbox((page.bbox[0], top, page.bbox[2], bottom))
    lines = (Line(raw["text"].strip(), float(raw["x1"])) for raw in band.extract_text_lines())
    return [line for line in lines if line.text]


def _clean_rows(raw: list[list[str | None]]) -> list[list[str]]:
    """Collapse line breaks inside cells and drop empty rows."""
    rows = [[" ".join((cell or "").split()) for cell in row] for row in raw]
    return [row for row in rows if any(row)]


def _page_items(page: Page, furniture: frozenset[str]) -> list[Item]:
    """Split a page into text bands and tables, top to bottom, so reading order is kept."""
    top_edge, bottom_edge = page.bbox[1], page.bbox[3]
    items: list[Item] = []
    cursor = top_edge
    for table in sorted(page.find_tables(), key=lambda t: t.bbox[1]):
        items.append(TextRun(tuple(_lines_between(page, cursor, table.bbox[1]))))
        items.append(Grid(_clean_rows(table.extract())))
        cursor = table.bbox[3]
    items.append(TextRun(tuple(_lines_between(page, cursor, bottom_edge))))
    return [_without_furniture(item, furniture) for item in items]


def _without_furniture(item: Item, furniture: frozenset[str]) -> Item:
    if isinstance(item, Grid):
        return item
    return TextRun(tuple(x for x in item.lines if _mask(x.text) not in furniture))


def merge_runs(items: Iterable[Item]) -> list[Item]:
    """Join adjacent text runs (also across page breaks) and drop empty ones."""
    merged: list[Item] = []
    for item in items:
        if isinstance(item, TextRun):
            if not item.lines:
                continue
            if merged and isinstance(merged[-1], TextRun):
                merged[-1] = TextRun(merged[-1].lines + item.lines)
                continue
        merged.append(item)
    return merged


class _Sections:
    """Accumulates lines and tables into one block per section, as the DOCX parser does."""

    def __init__(self, right_margin: float) -> None:
        self.blocks: list[Block] = []
        self._margin = right_margin
        self._heading = ""
        self._paragraphs: list[str] = []
        self._previous_was_full = False
        self._heading_emitted = False

    def add_line(self, line: Line) -> None:
        if is_section_heading(line.text):
            self.start_section(line.text)
            self._previous_was_full = False
            return
        # A fully upper-case line is a title or label ("BACKGROUND"): it never joins a neighbour.
        standalone = line.text.isupper()
        continues = (
            bool(self._paragraphs)
            and self._previous_was_full
            and not standalone
            and not _CLAUSE_START.match(line.text)
        )
        if continues:
            self._paragraphs[-1] += " " + line.text
        else:
            self._paragraphs.append(line.text)
        self._previous_was_full = not standalone and line.x1 >= self._margin - _WRAP_TOLERANCE_PT

    def add_table(self, rows: list[list[str]]) -> None:
        markdown = to_markdown_table(rows)
        if not markdown:
            return
        last = self._paragraphs[-1] if self._paragraphs else ""
        caption = last if len(last) <= _CAPTION_MAX_LEN else ""  # copied, not moved
        self._flush()
        head = "\n".join(part for part in (self._heading, caption) if part)
        text = f"{head}\n\n{markdown}" if head else markdown
        self.blocks.append(Block(kind=BlockKind.TABLE, text=text))
        self._heading_emitted = True
        self._previous_was_full = False

    def start_section(self, heading: str) -> None:
        self._flush()
        if self._heading and not self._heading_emitted:  # a heading must not vanish
            self.blocks.append(Block(kind=BlockKind.TEXT, text=self._heading))
        self._heading = heading
        self._heading_emitted = False

    def _flush(self) -> None:
        if not self._paragraphs:
            return
        lines = [self._heading, *self._paragraphs] if self._heading else self._paragraphs
        self.blocks.append(Block(kind=BlockKind.TEXT, text="\n".join(lines)))
        self._paragraphs = []
        self._heading_emitted = True


def assemble_blocks(items: Sequence[Item]) -> list[Block]:
    margin = max((x.x1 for i in items if isinstance(i, TextRun) for x in i.lines), default=0.0)
    sections = _Sections(margin)
    for item in items:
        if isinstance(item, Grid):
            sections.add_table(item.rows)
        else:
            for line in item.lines:
                sections.add_line(line)
    sections.start_section("")  # flush whatever is pending
    return sections.blocks


def parse_pdf(record: DocumentRecord, path: Path) -> ParsedDocument:
    """One TEXT block per section and one TABLE block per table, in reading order."""
    with pdfplumber.open(path) as pdf:
        pages = list(pdf.pages)
        raw = [[x.text for x in _lines_between(p, p.bbox[1], p.bbox[3])] for p in pages]
        furniture = find_page_furniture(raw)
        items = merge_runs(item for page in pages for item in _page_items(page, furniture))
    if not items:
        raise ValueError(f"{path.name}: no text layer (scanned?); use the OCR parser")
    return ParsedDocument(doc_id=record.doc_id, blocks=tuple(assemble_blocks(items)))
