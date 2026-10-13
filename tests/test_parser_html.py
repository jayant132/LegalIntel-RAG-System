from collections.abc import Callable
from pathlib import Path

from legalrag.domain import DocType
from legalrag.ingestion.manifest import DocumentRecord
from legalrag.ingestion.models import BlockKind, ParsedDocument
from legalrag.ingestion.parsers.html import parse_html

MakeRecord = Callable[..., DocumentRecord]


def _parse(tmp_path: Path, make_record: MakeRecord, html: str) -> ParsedDocument:
    p = tmp_path / "f.html"
    p.write_text(html, encoding="utf-8")
    return parse_html(make_record(DocType.POLICY, "html"), p)


def test_boilerplate_is_removed(tmp_path: Path, make_record: MakeRecord) -> None:
    html = (
        "<html><body><script>x()</script><div class='cookie'>We use cookies</div>"
        "<nav><li>Home</li></nav><p>Real content.</p><footer>(c) Terms</footer></body></html>"
    )
    doc = _parse(tmp_path, make_record, html)
    assert doc.text == "Real content."


def test_heading_is_attached_to_following_paragraph(
    tmp_path: Path, make_record: MakeRecord
) -> None:
    html = "<body><h2>Legal hold</h2><p>Suspend destruction.</p></body>"
    doc = _parse(tmp_path, make_record, html)
    assert doc.blocks[0].text == "Legal hold\n\nSuspend destruction."


def test_table_becomes_one_markdown_table_block(tmp_path: Path, make_record: MakeRecord) -> None:
    html = (
        "<body><table><tr><th>Type</th><th>Years</th></tr>"
        "<tr><td>Contracts</td><td>7</td></tr></table></body>"
    )
    doc = _parse(tmp_path, make_record, html)
    assert len(doc.blocks) == 1
    assert doc.blocks[0].kind is BlockKind.TABLE
    assert "| Contracts | 7 |" in doc.blocks[0].text


def test_real_retention_policy(manifest: dict[str, DocumentRecord], data_dir: Path) -> None:
    rec = manifest["D10"]
    doc = parse_html(rec, data_dir / rec.path)

    for noise in (
        "cookies",
        "Accept all",
        "Was this page helpful",
        "HR Portal",
        "Sitemap",
    ):
        assert noise not in doc.text

    assert "Last reviewed: 14 February 2023" in doc.text

    tables = [b for b in doc.blocks if b.kind is BlockKind.TABLE]
    assert len(tables) == 1
    assert "| Executed commercial contracts and amendments | 7 years |" in tables[0].text
    assert "Legal Hold" in doc.text
