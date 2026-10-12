import json

import pytest

from legalrag.observability import configure_logging, get_logger


def test_json_logging(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", json_output=True)
    get_logger("t").info("indexed", doc_id="D01", chunks=12)
    line = capsys.readouterr().err.strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["event"] == "indexed"
    assert payload["doc_id"] == "D01"
    assert payload["level"] == "info"


def test_level_filtering(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("WARNING", json_output=True)
    get_logger("t").info("hidden")
    assert capsys.readouterr().err.strip() == ""
