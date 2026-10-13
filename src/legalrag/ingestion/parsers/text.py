"""Plain-text parser: policies, notes, email threads and chat exports.

The structure of a .txt file depends on what kind of document it is, so the manifest's
``doc_type`` (not content sniffing) decides how it is split into blocks.
"""

from __future__ import annotations

import re
from pathlib import Path

from legalrag.domain import DocType
from legalrag.ingestion.manifest import DocumentRecord
from legalrag.ingestion.models import Block, BlockKind, ParsedDocument
from legalrag.ingestion.parsers._common import clean_multiline

_EMAIL_SEPARATOR = re.compile(
    r"^-{3,}\s*Original Message\s*-{3,}\s*$", re.IGNORECASE | re.MULTILINE
)
_CHAT_MESSAGE = re.compile(r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] ")
_BLANK_LINE = re.compile(r"\n\s*\n")


def _split_email(raw: str) -> list[str]:
    """One part per message, so each keeps its own From/Date headers."""
    return _EMAIL_SEPARATOR.split(raw)


def _split_chat(raw: str) -> list[str]:
    """One part per message; a line that doesn't start a message continues the previous one.

    Anything before the first message (the channel/export header) is its own part.
    """
    parts: list[str] = []
    for line in raw.split("\n"):
        if not line.strip():
            continue
        if _CHAT_MESSAGE.match(line) or not parts:
            parts.append(line)
        else:
            parts[-1] += "\n" + line
    return parts


def _split_paragraphs(raw: str) -> list[str]:
    return _BLANK_LINE.split(raw)


def parse_text(record: DocumentRecord, path: Path) -> ParsedDocument:
    """Parse a UTF-8 text file into blocks, using ``record.doc_type`` to pick the splitter."""
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if record.doc_type is DocType.EMAIL:
        parts = _split_email(raw)
    elif record.doc_type is DocType.CHAT:
        parts = _split_chat(raw)
    else:
        parts = _split_paragraphs(raw)
    blocks = tuple(
        Block(kind=BlockKind.TEXT, text=cleaned)
        for part in parts
        if (cleaned := clean_multiline(part))
    )
    return ParsedDocument(doc_id=record.doc_id, blocks=blocks)
