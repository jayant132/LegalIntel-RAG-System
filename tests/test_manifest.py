from datetime import date
from pathlib import Path

import pytest

from legalrag.domain import AuthorityTier, DocStatus
from legalrag.ingestion.manifest import load_manifest, parse_status


@pytest.mark.parametrize(
    ("raw", "status", "related"),
    [
        ("active", DocStatus.ACTIVE, ()),
        ("active (latest)", DocStatus.ACTIVE, ()),
        ("active (as amended by D04, D05)", DocStatus.ACTIVE, ("D04", "D05")),
        ("partially superseded by D05", DocStatus.PARTIALLY_SUPERSEDED, ("D05",)),
        ("superseded", DocStatus.SUPERSEDED, ()),
        ("partially stale", DocStatus.STALE, ()),
        ("informal - non-contractual", DocStatus.INFORMAL, ()),
        ("informal - non-authoritative", DocStatus.INFORMAL, ()),
    ],
)
def test_parse_status(raw: str, status: DocStatus, related: tuple[str, ...]) -> None:
    parsed = parse_status(raw)
    assert parsed.status is status
    assert parsed.related_doc_ids == related


def test_parse_status_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Unrecognised"):
        parse_status("kinda old")


def test_real_manifest_loads(data_dir: Path) -> None:
    docs = load_manifest(data_dir / "eval" / "document_manifest.csv")
    assert len(docs) == 17
    assert docs["D01"].acl_groups == {"legal", "procurement", "finance"}
    assert docs["D01"].authority is AuthorityTier.BINDING
    assert docs["D05"].effective_date == date(2024, 10, 1)
    assert docs["D09"].status is DocStatus.SUPERSEDED
    assert docs["D17"].needs_ocr and docs["D17"].file_format == "pdf"
    assert not docs["D01"].needs_ocr


def test_every_manifest_path_exists_on_disk(data_dir: Path) -> None:
    docs = load_manifest(data_dir / "eval" / "document_manifest.csv")
    missing = [d.doc_id for d in docs.values() if not (data_dir / d.path).is_file()]
    assert missing == []


def test_related_ids_point_to_real_documents(data_dir: Path) -> None:
    docs = load_manifest(data_dir / "eval" / "document_manifest.csv")
    for d in docs.values():
        assert set(d.related_doc_ids) <= docs.keys(), d.doc_id


def test_duplicate_ids_rejected(tmp_path: Path) -> None:
    header = (
        "doc_id,path,doc_type,entity,owner_dept,confidentiality,acl_groups,"
        "effective_date,version,status,language,format\n"
    )
    row = "D01,a.pdf,contract,E,Legal,internal,legal,2022-01-01,v1,active,en,pdf\n"
    p = tmp_path / "m.csv"
    p.write_text(header + row + row)
    with pytest.raises(ValueError, match="Duplicate"):
        load_manifest(p)
