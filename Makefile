.PHONY: screenshots preflight sync system-deps test lint format typecheck check session-log

screenshots:
	uv run python scripts/screenshots.py

preflight:
	python3 scripts/preflight.py

# Linux only: installs the system libraries Qt needs (and Xvfb for headless GUI
# tests), choosing apt or dnf from /etc/os-release. See scripts/system_deps.py.
# Not needed on Windows or macOS.
system-deps:
	python3 scripts/system_deps.py

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
