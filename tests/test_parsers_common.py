from legalrag.ingestion.parsers._common import clean_multiline, collapse_spaces, to_markdown_table


def test_clean_multiline_keeps_lines_but_trims_noise() -> None:
    raw = "  a  \r\n\r\n\r\n\r\nb\u00a0 \n"
    assert clean_multiline(raw) == "a\n\nb"


def test_collapse_spaces_flattens_newlines_and_nbsp() -> None:
    assert collapse_spaces("a \n\t b\u00a0\u00a0c") == "a b c"


def test_markdown_table_has_header_separator_and_rows() -> None:
    md = to_markdown_table([["Name", "Days"], ["Orbis", "90"]])
    assert md == "| Name | Days |\n| --- | --- |\n| Orbis | 90 |"


def test_markdown_table_escapes_pipes_and_pads_short_rows() -> None:
    md = to_markdown_table([["A", "B"], ["x|y"]])
    assert md.splitlines()[2] == "| x\\|y |  |"


def test_markdown_table_empty() -> None:
    assert to_markdown_table([]) == ""
