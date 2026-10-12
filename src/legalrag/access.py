"""Access-control rule: the single source of truth, reused by retrieval filters."""

from __future__ import annotations

from collections.abc import Iterable

ALL_EMPLOYEES = "all-employees"


def is_allowed(user_group: str, acl_groups: Iterable[str]) -> bool:
    """A user may read a document if the ACL names their group or grants all employees."""
    acl = set(acl_groups)
    return ALL_EMPLOYEES in acl or user_group in acl
