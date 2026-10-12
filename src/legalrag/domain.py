"""Core domain vocabulary shared by ingestion, retrieval, generation and evaluation."""

from __future__ import annotations

from enum import Enum


class DocStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    PARTIALLY_SUPERSEDED = "partially_superseded"
    STALE = "stale"
    INFORMAL = "informal"


class AuthorityTier(int, Enum):
    """How much a source may be trusted when sources conflict (higher wins)."""

    INFORMAL = 1  # email, chat, meeting notes
    RECORD = 2  # memos, minutes, reports, registers
    POLICY = 3  # internal policies
    BINDING = 4  # executed contracts and amendments


class ExpectedBehavior(str, Enum):
    """What a correct system does for an evaluation question."""

    ANSWER = "answer"
    ABSTAIN_NOT_IN_CORPUS = "abstain_not_in_corpus"
    REFUSE_ACCESS_DENIED = "refuse_access_denied"
    ANSWER_STATING_ABSENCE = "answer_stating_absence"
