from pathlib import Path

import pytest

from legalrag.ingestion.manifest import DocumentRecord
from legalrag.ingestion.models import BlockKind, ParsedDocument
from legalrag.ingestion.parsers.pdf import (
    Grid,
    Line,
    TextRun,
    assemble_blocks,
    find_page_furniture,
    merge_runs,
    parse_pdf,
)

MARGIN = 540.0


def full(text: str) -> Line:
    """A line that reaches the right margin, i.e. one that wraps onto the next line."""
    return Line(text, MARGIN)


def short(text: str) -> Line:
    """A line that ends well before the margin, i.e. the end of a paragraph."""
    return Line(text, 200.0)


def texts(items: list[TextRun | Grid]) -> list[str]:
    return [b.text for b in assemble_blocks(items)]


# --- page furniture ---------------------------------------------------------------------


def test_furniture_is_found_with_page_numbers_masked() -> None:
    pages = [
        ["Agreement - CONFIDENTIAL", "Body one", "Ref/1 | Page 1"],
        ["Agreement - CONFIDENTIAL", "Body two", "Ref/1 | Page 2"],
        ["Agreement - CONFIDENTIAL", "Body three", "Ref/1 | Page 3"],
    ]
    assert find_page_furniture(pages) == {"Agreement - CONFIDENTIAL", "Ref/# | Page #"}


def test_header_missing_on_the_cover_page_is_still_found() -> None:
    pages = [["Cover"], ["Header", "A"], ["Header", "B"]]
    assert "Header" in find_page_furniture(pages)


def test_repeated_body_sentence_is_not_furniture() -> None:
    middle = "Signature required here."
    pages = [["Top 1", "x", "y", middle, "p", "q", "Bottom 1"]] * 2
    assert middle not in find_page_furniture(pages)


def test_a_single_page_has_no_furniture() -> None:
    assert find_page_furniture([["Header", "Body", "Footer"]]) == frozenset()


# --- paragraph and section assembly -----------------------------------------------------


def test_wrapped_lines_are_rejoined_and_paragraph_ends_are_kept() -> None:
    run = TextRun((full("the first half of a long"), short("sentence."), short("Next.")))
    assert texts([run]) == ["the first half of a long sentence.\nNext."]


def test_a_clause_number_starts_a_new_paragraph_even_after_a_full_line() -> None:
    run = TextRun((full("3.1 First clause that fills the line"), full("3.2 Second clause.")))
    assert texts([run]) == ["3.1 First clause that fills the line\n3.2 Second clause."]


def test_upper_case_lines_stand_alone() -> None:
    run = TextRun(
        (full("(2) Nordhaven, the Supplier)."), short("BACKGROUND"), short("(A) Context."))
    )
    assert texts([run]) == ["(2) Nordhaven, the Supplier).\nBACKGROUND\n(A) Context."]


def test_a_section_split_by_a_page_break_stays_together() -> None:
    page_one = TextRun((full("filler"), short("3. THE SERVICES")))
    page_two = TextRun((short("3.1 Nordhaven shall provide the Services."),))
    merged = merge_runs([page_one, page_two])
    assert len(merged) == 1
    assert texts(merged)[-1] == "3. THE SERVICES\n3.1 Nordhaven shall provide the Services."


def test_merge_runs_drops_empty_runs_and_keeps_tables_as_separators() -> None:
    grid = Grid([["a", "b"], ["1", "2"]])
    merged = merge_runs([TextRun(()), TextRun((short("x"),)), grid, TextRun((short("y"),))])
    assert [type(m).__name__ for m in merged] == ["TextRun", "Grid", "TextRun"]


def test_table_block_carries_heading_and_short_caption() -> None:
    items: list[TextRun | Grid] = [
        TextRun((short("SCHEDULE 1 - FEES"), short("Part A: Fees (EUR)"))),
        Grid([["Ref", "Fee"], ["1.1", "42,000"]]),
    ]
    blocks = assemble_blocks(items)
    assert [b.kind for b in blocks] == [BlockKind.TEXT, BlockKind.TABLE]
    assert blocks[0].text == "SCHEDULE 1 - FEES\nPart A: Fees (EUR)"
    assert blocks[1].text.startswith("SCHEDULE 1 - FEES\nPart A: Fees (EUR)\n\n| Ref | Fee |")


def test_long_paragraph_before_a_table_is_not_used_as_caption() -> None:
    long_intro = "word " * 40
    items: list[TextRun | Grid] = [
        TextRun((short("2. Fees"), short(long_intro.strip()))),
        Grid([["a", "b"], ["1", "2"]]),
    ]
    table = assemble_blocks(items)[1]
    assert table.text.startswith("2. Fees\n\n| a | b |")


def test_heading_without_content_is_not_lost() -> None:
    run = TextRun((short("1. Lonely heading"), short("2. Next"), short("Body.")))
    assert texts([run]) == ["1. Lonely heading", "2. Next\nBody."]


# --- the real documents -----------------------------------------------------------------


def _parse(manifest: dict[str, DocumentRecord], data_dir: Path, doc_id: str) -> ParsedDocument:
    record = manifest[doc_id]
    return parse_pdf(record, data_dir / record.path)


def test_msa_has_no_running_header_or_footer(
    manifest: dict[str, DocumentRecord], data_dir: Path
) -> None:
    text = _parse(manifest, data_dir, "D01").text
    assert "Master Services Agreement - Veridian" not in text
    assert "Execution version" not in text


def test_msa_clause_3_is_stitched_across_the_page_break(
    manifest: dict[str, DocumentRecord], data_dir: Path
) -> None:
    blocks = _parse(manifest, data_dir, "D01").blocks
    clause_3 = next(b for b in blocks if b.text.startswith("3. THE SERVICES"))
    assert clause_3.text.splitlines()[1].startswith("3.1 Nordhaven shall provide")


def test_msa_tables_are_extracted_once(manifest: dict[str, DocumentRecord], data_dir: Path) -> None:
    parsed = _parse(manifest, data_dir, "D01")
    tables = [b for b in parsed.blocks if b.kind is BlockKind.TABLE]
    assert len(tables) == 3
    assert parsed.text.count("71,500") == 1  # not repeated as scrambled body text
    fees = tables[0].text
    assert fees.startswith("SCHEDULE 1 - SERVICES AND FEES\nPart A:")
    assert "| 1.2 | Managed Service Desk |" in fees
    assert "| Below 99.0% | 20% |" in tables[2].text


def test_msa_keeps_the_drafting_footnote(
    manifest: dict[str, DocumentRecord], data_dir: Path
) -> None:
    assert "Final: 36 months." in _parse(manifest, data_dir, "D01").blocks[-1].text


def test_msa_block_count_is_stable(manifest: dict[str, DocumentRecord], data_dir: Path) -> None:
    assert len(_parse(manifest, data_dir, "D01").blocks) == 27


def test_dpa_table_cells_have_no_embedded_line_breaks(
    manifest: dict[str, DocumentRecord], data_dir: Path
) -> None:
    parsed = _parse(manifest, data_dir, "D02")
    table = next(b for b in parsed.blocks if b.kind is BlockKind.TABLE)
    assert "| Amazon Web Services EMEA SARL |" in table.text
    assert table.text.startswith("4. Sub-processors\n\n")
    assert len(parsed.blocks) == 11


def test_nda_sections(manifest: dict[str, DocumentRecord], data_dir: Path) -> None:
    parsed = _parse(manifest, data_dir, "D03")
    assert len(parsed.blocks) == 14
    assert parsed.blocks[12].text.startswith("12. Governing law")


def test_memo_banner_and_title_stay_separate_lines(
    manifest: dict[str, DocumentRecord], data_dir: Path
) -> None:
    parsed = _parse(manifest, data_dir, "D14")
    assert parsed.blocks[0].text.splitlines()[-1] == "MEMORANDUM"
    header = parsed.blocks[1]
    assert header.kind is BlockKind.TABLE
    assert "| To | Tomas Vidal, General Counsel |" in header.text
    assert parsed.blocks[-1].text.startswith("6. Recommendations")


def test_scanned_pdf_is_rejected_with_a_pointer_to_ocr(
    manifest: dict[str, DocumentRecord], data_dir: Path
) -> None:
    with pytest.raises(ValueError, match="no text layer"):
        _parse(manifest, data_dir, "D17")
