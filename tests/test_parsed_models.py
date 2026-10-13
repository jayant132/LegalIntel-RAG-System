import pytest
from pydantic import ValidationError

from legalrag.ingestion.models import Block, BlockKind, ParsedDocument


def test_block_rejects_blank_text() -> None:
    with pytest.raises(ValidationError):
        Block(kind=BlockKind.TEXT, text="   ")


def test_block_rejects_page_zero() -> None:
    with pytest.raises(ValidationError):
        Block(kind=BlockKind.TEXT, text="x", page=0)


def test_parsed_document_rejects_empty() -> None:
    with pytest.raises(ValidationError, match="no content"):
        ParsedDocument(doc_id="D01", blocks=())


def test_parsed_document_text_joins_blocks_in_order() -> None:
    doc = ParsedDocument(
        doc_id="D01",
        blocks=(
            Block(kind=BlockKind.TEXT, text="first", page=1),
            Block(kind=BlockKind.TABLE, text="| a |\n| - |", page=2),
        ),
    )
    assert doc.text == "first\n\n| a |\n| - |"
