from collections.abc import Callable
from datetime import date
from pathlib import Path

import pytest

from legalrag.domain import DocStatus, DocType
from legalrag.ingestion.manifest import DocumentRecord, load_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return REPO_ROOT / "data"


@pytest.fixture(scope="session")
def manifest(data_dir: Path) -> dict[str, DocumentRecord]:
    return load_manifest(data_dir / "eval" / "document_manifest.csv")


@pytest.fixture
def make_record() -> Callable[..., DocumentRecord]:
    """Build a minimal DocumentRecord for synthetic parser tests."""

    def _make(doc_type: DocType, file_format: str = "txt") -> DocumentRecord:
        return DocumentRecord(
            doc_id="D99",
            path=Path("x"),
            doc_type=doc_type,
            entity="E",
            owner_dept="Legal",
            confidentiality="internal",
            acl_groups=frozenset({"legal"}),
            effective_date=date(2024, 1, 1),
            version="v1",
            status=DocStatus.ACTIVE,
            status_raw="active",
            related_doc_ids=(),
            language="en",
            file_format=file_format,
            needs_ocr=False,
        )

    return _make
