"""Heading heuristics shared by parsers of legal documents that carry no real heading styles."""

from __future__ import annotations

import re

MAX_HEADING_LEN = 90
_SENTENCE_PUNCTUATION = (".", ";", ":", ",")

_NUMBERED = re.compile(r"^\d+\.\s+\S")
_ANNEX = re.compile(r"^(?:SCHEDULE|ANNEX|APPENDIX|EXHIBIT)\s+\S")


def _is_short_label(text: str) -> bool:
    return len(text) <= MAX_HEADING_LEN and not text.endswith(_SENTENCE_PUNCTUATION)


def is_numbered_heading(text: str) -> bool:
    """``3. Gifts and hospitality``: a number, a short line, no sentence-ending punctuation.

    A full sentence that merely starts with a number (``2. This applies to all staff.``)
    is not a heading.
    """
    return bool(_NUMBERED.match(text)) and _is_short_label(text)


def is_section_heading(text: str) -> bool:
    """Numbered headings, plus upper-case annex titles such as ``SCHEDULE 2 - SERVICE LEVELS``."""
    if is_numbered_heading(text):
        return True
    return bool(_ANNEX.match(text)) and text.isupper() and _is_short_label(text)
