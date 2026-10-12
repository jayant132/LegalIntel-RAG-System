import pytest

from legalrag.settings import Settings


def test_defaults() -> None:
    s = Settings(_env_file=None)
    assert s.embed_model == "nomic-embed-text"
    assert s.generator_model == "llama3.2:3b"
    assert s.use_embed_prefixes is True


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEGALRAG_GENERATOR_MODEL", "qwen2.5:7b-instruct")
    monkeypatch.setenv("LEGALRAG_LOG_JSON", "true")
    s = Settings(_env_file=None)
    assert s.generator_model == "qwen2.5:7b-instruct"
    assert s.log_json is True


def test_invalid_log_level_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEGALRAG_LOG_LEVEL", "LOUD")
    with pytest.raises(ValueError):
        Settings(_env_file=None)
