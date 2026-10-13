"""Helpers shared by several parsers."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

_MULTI_BLANK = re.compile(r"\n{3,}")
_MULTI_SPACE = re.compile(r"[ \t\u00a0]+")


def clean_multiline(text: str) -> str:
    """Normalise a multi-line string but keep its line structure.

    Used for emails, policies and notes, where each line (e.g. ``3.1 Gifts ...``) matters.
    """
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    return _MULTI_BLANK.sub("\n\n", "\n".join(lines)).strip()


def collapse_spaces(text: str) -> str:
    """Collapse all runs of whitespace (including newlines) into single spaces."""
    return _MULTI_SPACE.sub(" ", re.sub(r"\s+", " ", unicodedata.normalize("NFC", text))).strip()


def to_markdown_table(rows: Sequence[Sequence[str]]) -> str:
    """Render rows (first row = header) as a markdown table.

    Markdown keeps each value next to its column name, which a flattened row would lose.
    """
    if not rows:
        return ""
    width = max(len(r) for r in rows)

    def cell(value: str) -> str:
        return collapse_spaces(value).replace("|", "\\|")

    def line(r: Sequence[str]) -> str:
        padded = [cell(c) for c in r] + [""] * (width - len(r))
        return "| " + " | ".join(padded) + " |"

    header, *body = rows
    out = [line(header), "| " + " | ".join(["---"] * width) + " |"]
    out.extend(line(r) for r in body)
    return "\n".join(out)
