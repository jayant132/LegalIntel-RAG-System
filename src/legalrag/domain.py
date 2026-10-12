"""Core domain vocabulary shared by ingestion, retrieval, generation and evaluation."""

from __future__ import annotations

from enum import Enum


class DocStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    PARTIALLY_SUPERSEDED = "partially_superseded"
    STALE = "stale"
    INFORMAL = "informal"


class DocType(str, Enum):
    """Kinds of document in the corpus. Unknown values fail loudly at load time."""

    CONTRACT = "contract"
    AMENDMENT = "amendment"
    EMPLOYMENT = "employment"
    POLICY = "policy"
    BOARD_MINUTES = "board_minutes"
    LEGAL_MEMO = "legal_memo"
    REPORT = "report"
    REGISTER = "register"
    EMAIL = "email"
    CHAT = "chat"
    NOTES = "notes"


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


DOC_TYPE_AUTHORITY: dict[DocType, AuthorityTier] = {
    DocType.CONTRACT: AuthorityTier.BINDING,
    DocType.AMENDMENT: AuthorityTier.BINDING,
    DocType.EMPLOYMENT: AuthorityTier.BINDING,
    DocType.POLICY: AuthorityTier.POLICY,
    DocType.BOARD_MINUTES: AuthorityTier.RECORD,
    DocType.LEGAL_MEMO: AuthorityTier.RECORD,
    DocType.REPORT: AuthorityTier.RECORD,
    DocType.REGISTER: AuthorityTier.RECORD,
    DocType.EMAIL: AuthorityTier.INFORMAL,
    DocType.CHAT: AuthorityTier.INFORMAL,
    DocType.NOTES: AuthorityTier.INFORMAL,
}
