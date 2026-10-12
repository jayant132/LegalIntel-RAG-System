.PHONY: install lint format typecheck test check hooks

install:  ## create .venv and install pinned deps (uv)
	uv sync --extra dev

lint:  ## static analysis
	uv run ruff check .
	uv run ruff format --check .

format:  ## auto-fix style
	uv run ruff check --fix .
	uv run ruff format .

typecheck:
	uv run mypy

test:
	uv run pytest

check: lint typecheck test  ## everything CI runs

hooks:  ## install git pre-commit hooks
	uv run pre-commit install
