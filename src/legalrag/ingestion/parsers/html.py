"""HTML parser: keep the policy content, drop the website around it."""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup, Tag

from legalrag.ingestion.manifest import DocumentRecord
from legalrag.ingestion.models import Block, BlockKind, ParsedDocument
from legalrag.ingestion.parsers._common import collapse_spaces, to_markdown_table

# Tags that never contain document content.
_BOILERPLATE_TAGS = ("script", "style", "noscript", "nav", "footer", "aside", "form", "button")
# Class/id fragments that mark banners and navigation helpers.
_BOILERPLATE_HINTS = ("cookie", "breadcrumb", "consent", "banner")
_HEADINGS = ("h1", "h2", "h3", "h4")
_CONTENT_TAGS = (*_HEADINGS, "p", "li", "table")


def _is_boilerplate(tag: Tag) -> bool:
    attrs = " ".join([*tag.get_attribute_list("class"), *tag.get_attribute_list("id")]).lower()
    return any(hint in attrs for hint in _BOILERPLATE_HINTS)


def _table_rows(table: Tag) -> list[list[str]]:
    return [
        [cell.get_text(" ", strip=True) for cell in tr.find_all(["th", "td"])]
        for tr in table.find_all("tr")
    ]


def parse_html(record: DocumentRecord, path: Path) -> ParsedDocument:
    """Strip boilerplate, then emit text blocks (headings attached to what follows) and tables."""
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")
    for tag in soup(list(_BOILERPLATE_TAGS)):
        tag.decompose()
    for tag in [t for t in soup.find_all(True) if isinstance(t, Tag) and _is_boilerplate(t)]:
        tag.decompose()

    blocks: list[Block] = []
    pending_heading = ""

    def emit(text: str, kind: BlockKind) -> None:
        nonlocal pending_heading
        full = f"{pending_heading}\n\n{text}" if pending_heading else text
        blocks.append(Block(kind=kind, text=full))
        pending_heading = ""

    body = soup.body or soup
    for el in body.find_all(_CONTENT_TAGS):
        if not isinstance(el, Tag):
            continue
        # Skip cells' inner paragraphs/lists: tables are handled whole, once.
        if el.name != "table" and el.find_parent("table"):
            continue
        if el.name == "table":
            md = to_markdown_table(_table_rows(el))
            if md:
                emit(md, BlockKind.TABLE)
            continue
        text = collapse_spaces(el.get_text(" ", strip=True))
        if not text:
            continue
        if el.name in _HEADINGS:
            pending_heading = f"{pending_heading}\n{text}".strip()
        else:
            emit(text, BlockKind.TEXT)
    if pending_heading:  # a trailing heading with nothing after it
        emit(pending_heading, BlockKind.TEXT)
    return ParsedDocument(doc_id=record.doc_id, blocks=tuple(blocks))
