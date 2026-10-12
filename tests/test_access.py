from legalrag.access import is_allowed


def test_named_group_allowed() -> None:
    assert is_allowed("legal", ["legal", "procurement"])


def test_other_group_denied() -> None:
    assert not is_allowed("finance", ["hr", "legal"])


def test_all_employees_grants_everyone() -> None:
    assert is_allowed("procurement", ["all-employees"])


def test_all_employees_user_is_not_a_wildcard() -> None:
    assert not is_allowed("all-employees", ["legal"])


def test_empty_acl_denies() -> None:
    assert not is_allowed("legal", [])
