"""Typed loader for ``golden_questions.json``."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, TypeAdapter

from legalrag.domain import ExpectedBehavior


class GoldenQuestion(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    category: str
    difficulty: Literal["easy", "medium", "hard"]
    question: str
    # null for access-denied questions: a refusal has no "correct answer text"
    ground_truth: str | None
    source_docs: tuple[str, ...]
    user_group_asking: str
    should_answer: bool
    notes: str = ""
    expected_behavior: ExpectedBehavior


_ADAPTER = TypeAdapter(list[GoldenQuestion])


def load_golden(path: Path) -> list[GoldenQuestion]:
    """Load and validate the golden set; duplicate ids are rejected."""
    questions = _ADAPTER.validate_json(path.read_text(encoding="utf-8"))
    ids = [q.id for q in questions]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate question ids in golden set")
    return questions
