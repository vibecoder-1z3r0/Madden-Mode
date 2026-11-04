.PHONY: sync test lint format typecheck check

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
