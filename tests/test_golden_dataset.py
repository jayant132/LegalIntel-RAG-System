"""Data-integrity tests: the eval set must be consistent with the manifest.

A golden set with contradictions silently caps your measurable accuracy, so we
test the data the same way we test code.
"""

from pathlib import Path

import pytest

from legalrag.access import is_allowed
from legalrag.domain import ExpectedBehavior
from legalrag.evaluation.dataset import GoldenQuestion, load_golden
from legalrag.ingestion.manifest import load_manifest

DATA = Path(__file__).resolve().parents[1] / "data"
GOLDEN = load_golden(DATA / "eval" / "golden_questions.json")

# Known defects: asked by 'exec', but cited sources include documents exec may not read.
# strict xfail => once you fix the data, the test fails and tells you to delete the id here.
KNOWN_ACL_INCONSISTENT = {"Q24", "Q40"}


def test_golden_has_40_unique_questions() -> None:
    assert len(GOLDEN) == 40
    assert len({q.id for q in GOLDEN}) == 40


def test_source_docs_exist_in_manifest() -> None:
    docs = load_manifest(DATA / "eval" / "document_manifest.csv")
    for q in GOLDEN:
        assert set(q.source_docs) <= docs.keys(), q.id


def test_should_answer_flag_matches_expected_behavior() -> None:
    answers = {ExpectedBehavior.ANSWER, ExpectedBehavior.ANSWER_STATING_ABSENCE}
    for q in GOLDEN:
        assert q.should_answer == (q.expected_behavior in answers), q.id


def test_answerable_questions_have_ground_truth() -> None:
    for q in GOLDEN:
        if q.should_answer:
            assert q.ground_truth, q.id


def _acl_cases() -> list[object]:
    xfail = pytest.mark.xfail(strict=True, reason="golden-set ACL defect")
    return [
        pytest.param(q, id=q.id, marks=[xfail] if q.id in KNOWN_ACL_INCONSISTENT else [])
        for q in GOLDEN
    ]


@pytest.mark.parametrize("q", _acl_cases())
def test_acl_consistency(q: GoldenQuestion) -> None:
    """Answerable questions must be answerable from docs the asker may read;
    access-denied questions must cite at least one doc the asker may NOT read."""
    docs = load_manifest(DATA / "eval" / "document_manifest.csv")
    allowed = [is_allowed(q.user_group_asking, docs[d].acl_groups) for d in q.source_docs]
    if q.expected_behavior is ExpectedBehavior.REFUSE_ACCESS_DENIED:
        assert not all(allowed)
    elif q.source_docs:
        assert all(allowed)
