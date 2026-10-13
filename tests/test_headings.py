import pytest

from legalrag.ingestion.parsers._headings import is_numbered_heading, is_section_heading


@pytest.mark.parametrize(
    "text",
    ["3. Gifts and hospitality", "3. THE SERVICES", "10. Non-solicitation"],
)
def test_numbered_headings(text: str) -> None:
    assert is_numbered_heading(text)


@pytest.mark.parametrize(
    "text",
    [
        "2. This is a full sentence that ends with a period.",
        "2. Incident response and resolution.",
        "3.1 Nordhaven shall provide the Services",
        "Gifts and hospitality",
        "1. " + "word " * 30,
    ],
)
def test_not_numbered_headings(text: str) -> None:
    assert not is_numbered_heading(text)


def test_annex_titles_must_be_upper_case() -> None:
    assert is_section_heading("SCHEDULE 2 - SERVICE LEVELS AND SERVICE CREDITS")
    assert not is_section_heading("Schedule 2 shall apply to all services.")
    assert not is_section_heading("SCHEDULE 2 APPLIES TO ALL SERVICES.")
