"""Load ``document_manifest.csv`` into validated, typed records.

The manifest is the single source of truth for per-document metadata (access control,
version, status). Everything downstream derives from it, so bad rows must fail here,
loudly, rather than silently corrupting the index.
"""

from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from legalrag.domain import DOC_TYPE_AUTHORITY, AuthorityTier, DocStatus, DocType

_DOC_REF = re.compile(r"\bD\d{2}\b")


class ParsedStatus(BaseModel):
    """A free-text manifest status turned into structured fields."""

    model_config = ConfigDict(frozen=True)

    status: DocStatus
    related_doc_ids: tuple[str, ...] = ()


def parse_status(raw: str) -> ParsedStatus:
    """Map text like 'partially superseded by D05' to a DocStatus + related doc ids.

    Order matters: 'partially superseded' must be tested before 'superseded'.
    Raises ValueError on anything unrecognised (fail loudly, never guess).
    """
    text = raw.strip().lower()
    related = tuple(_DOC_REF.findall(raw))
    if text.startswith("partially superseded"):
        status = DocStatus.PARTIALLY_SUPERSEDED
    elif text.startswith("superseded"):
        status = DocStatus.SUPERSEDED
    elif "stale" in text:
        status = DocStatus.STALE
    elif text.startswith("informal"):
        status = DocStatus.INFORMAL
    elif text.startswith("active"):
        status = DocStatus.ACTIVE
    else:
        raise ValueError(f"Unrecognised document status: {raw!r}")
    return ParsedStatus(status=status, related_doc_ids=related)


class DocumentRecord(BaseModel):
    """One row of the manifest, validated and normalised."""

    model_config = ConfigDict(frozen=True)

    doc_id: str
    path: Path
    doc_type: DocType
    entity: str
    owner_dept: str
    confidentiality: str
    acl_groups: frozenset[str]
    effective_date: date
    version: str
    status: DocStatus
    status_raw: str
    related_doc_ids: tuple[str, ...]
    language: str
    file_format: str
    needs_ocr: bool

    @field_validator("doc_id")
    @classmethod
    def _check_doc_id(cls, v: str) -> str:
        if not re.fullmatch(r"D\d{2}", v):
            raise ValueError(f"doc_id must look like 'D01', got {v!r}")
        return v

    @field_validator("acl_groups", mode="before")
    @classmethod
    def _split_acl(cls, v: Any) -> Any:
        if isinstance(v, str):
            return frozenset(g.strip() for g in v.split(";") if g.strip())
        return v

    @model_validator(mode="after")
    def _acl_not_empty(self) -> DocumentRecord:
        # An empty ACL means "nobody can read this": almost certainly a data error.
        if not self.acl_groups:
            raise ValueError(f"{self.doc_id}: acl_groups must not be empty")
        return self

    @property
    def authority(self) -> AuthorityTier:
        return DOC_TYPE_AUTHORITY[self.doc_type]


def _row_to_record(row: dict[str, str]) -> DocumentRecord:
    parsed = parse_status(row["status"])
    fmt_raw = row["format"].strip().lower()
    return DocumentRecord(
        doc_id=row["doc_id"].strip(),
        path=Path(row["path"].strip()),
        doc_type=DocType(row["doc_type"].strip()),
        entity=row["entity"].strip(),
        owner_dept=row["owner_dept"].strip(),
        confidentiality=row["confidentiality"].strip(),
        acl_groups=row["acl_groups"],  # a str here; the before-validator splits it
        effective_date=date.fromisoformat(row["effective_date"].strip()),
        version=row["version"].strip(),
        status=parsed.status,
        status_raw=row["status"].strip(),
        related_doc_ids=parsed.related_doc_ids,
        language=row["language"].strip(),
        file_format=fmt_raw.split()[0],  # "pdf (image only, needs OCR)" -> "pdf"
        needs_ocr="ocr" in fmt_raw,
    )


def load_manifest(manifest_path: Path) -> dict[str, DocumentRecord]:
    """Read the manifest CSV and return {doc_id: DocumentRecord}.

    'utf-8-sig' strips a BOM if Excel wrote one.
    """
    with manifest_path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    records: dict[str, DocumentRecord] = {}
    for row in rows:
        record = _row_to_record(row)
        if record.doc_id in records:
            raise ValueError(f"Duplicate doc_id in manifest: {record.doc_id}")
        records[record.doc_id] = record
    return records
