.PHONY: sync system-deps test lint format typecheck check session-log

# Linux only: system libraries Qt needs to load and to run under a virtual
# display (Xvfb). Uses sudo unless already root. Not needed on Windows/macOS.
SUDO := $(shell [ "$$(id -u)" = 0 ] || echo sudo)
SYSTEM_DEPS := libegl1 libgl1 libxkbcommon0 libxkbcommon-x11-0 libdbus-1-3 \
	libfontconfig1 xvfb libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
	libxcb-keysyms1 libxcb-render-util0 libxcb-xinerama0 libxcb-xkb1 \
	libxcb-shape0

system-deps:
	$(SUDO) apt-get update
	$(SUDO) apt-get install -y $(SYSTEM_DEPS)

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
