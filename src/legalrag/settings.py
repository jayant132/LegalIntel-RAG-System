"""Typed, environment-driven configuration (prefix ``LEGALRAG_``)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LEGALRAG_",
        env_file=".env",
        extra="ignore",
    )

    ollama_host: str = "http://localhost:11434"
    ollama_timeout_s: float = 120.0

    embed_model: str = "nomic-embed-text"
    generator_model: str = "llama3.2:3b"
    judge_model: str = "qwen2.5:7b-instruct"
    use_embed_prefixes: bool = True

    data_dir: Path = Path("data")
    chroma_dir: Path = Path(".chroma")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_json: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Settings are read once per process and shared."""
    return Settings()
