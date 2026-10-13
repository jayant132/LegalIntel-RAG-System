"""Format-independent output of the parsers.

Every parser (PDF, DOCX, XLSX, HTML, TXT, OCR) returns a ``ParsedDocument``, so the
chunker never needs to know which format a document came from.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BlockKind(str, Enum):
    TEXT = "text"
    TABLE = "table"  # rendered as markdown so the structure survives chunking


class Block(BaseModel):
    """A contiguous piece of document text with its provenance."""

    model_config = ConfigDict(frozen=True)

    kind: BlockKind
    text: str
    page: int | None = Field(default=None, ge=1)
    ocr_confidence: float | None = Field(default=None, ge=0.0, le=100.0)

    @field_validator("text")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Block text must not be blank")
        return v


class ParsedDocument(BaseModel):
    """All blocks of one document, in reading order."""

    model_config = ConfigDict(frozen=True)

    doc_id: str
    blocks: tuple[Block, ...]

    @field_validator("blocks")
    @classmethod
    def _has_content(cls, v: tuple[Block, ...]) -> tuple[Block, ...]:
        # A parse that yields nothing (e.g. a scanned PDF read without OCR) must fail
        # loudly. Otherwise the document is silently missing from the index.
        if not v:
            raise ValueError("Parsed document has no content")
        return v

    @property
    def text(self) -> str:
        return "\n\n".join(b.text for b in self.blocks)
