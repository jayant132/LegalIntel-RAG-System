from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

from legalrag.domain import DocType
from legalrag.ingestion.manifest import DocumentRecord
from legalrag.ingestion.parsers.text import parse_text

MakeRecord = Callable[..., DocumentRecord]


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "f.txt"
    p.write_text(content, encoding="utf-8")
    return p


def test_email_split_keeps_each_message_with_its_headers(
    tmp_path: Path, make_record: MakeRecord
) -> None:
    raw = "From: A\nDate: 1\n\nhello\n\n-----Original Message-----\nFrom: B\nDate: 0\n\nearlier"
    doc = parse_text(make_record(DocType.EMAIL), _write(tmp_path, raw))
    assert len(doc.blocks) == 2
    assert doc.blocks[0].text.startswith("From: A")
    assert doc.blocks[1].text.startswith("From: B")


def test_chat_one_block_per_message_with_continuation(
    tmp_path: Path, make_record: MakeRecord
) -> None:
    raw = (
        "#chan (exported)\n\n"
        "[2024-12-03 17:02] a: first\n"
        "second line of first\n"
        "[2024-12-03 17:03] b: reply\n"
    )
    doc = parse_text(make_record(DocType.CHAT), _write(tmp_path, raw))
    assert [b.text.split("\n")[0][:12] for b in doc.blocks] == [
        "#chan (expor",
        "[2024-12-03 ",
        "[2024-12-03 ",
    ]
    assert doc.blocks[1].text.endswith("second line of first")


def test_policy_splits_on_blank_lines_keeping_clause_lines_together(
    tmp_path: Path, make_record: MakeRecord
) -> None:
    raw = "3. GIFTS\n3.1 a\n3.2 b\n\n4. THIRD PARTIES\ntext\n"
    doc = parse_text(make_record(DocType.POLICY), _write(tmp_path, raw))
    assert len(doc.blocks) == 2
    assert doc.blocks[0].text == "3. GIFTS\n3.1 a\n3.2 b"


def test_empty_file_fails_loudly(tmp_path: Path, make_record: MakeRecord) -> None:
    with pytest.raises(ValidationError, match="no content"):
        parse_text(make_record(DocType.NOTES), _write(tmp_path, "\n\n  \n"))


def test_real_email_thread(manifest: dict[str, DocumentRecord], data_dir: Path) -> None:
    rec = manifest["D11"]
    doc = parse_text(rec, data_dir / rec.path)
    assert len(doc.blocks) == 2
    assert "99.12%" in doc.blocks[0].text
    assert doc.blocks[1].text.startswith("From: Marcus Hale")


def test_real_slack_export(manifest: dict[str, DocumentRecord], data_dir: Path) -> None:
    rec = manifest["D12"]
    doc = parse_text(rec, data_dir / rec.path)
    assert len(doc.blocks) == 18  # channel header + 17 messages
    assert "A2 put it back to 180" in doc.text


def test_real_policy_clauses_survive(manifest: dict[str, DocumentRecord], data_dir: Path) -> None:
    rec = manifest["D09"]
    doc = parse_text(rec, data_dir / rec.path)
    assert "3.1 Gifts with a value exceeding GBP 150" in doc.text
