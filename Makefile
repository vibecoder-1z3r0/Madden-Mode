.PHONY: sync test lint format typecheck check session-log

sync:
	uv sync --extra dev

test:
	uv run pytest tests --cov=maddenmode --cov-report=term-missing

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .

typecheck:
	uv run mypy src/

check: lint typecheck test

# Usage: make session-log SESSION=<session-id>
session-log:
	python3 scripts/session_timing.py $(SESSION) > SESSION_LOG.md
