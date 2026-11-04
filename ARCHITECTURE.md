# Architecture

Madden Mode: telestration (drawing/annotation) over a game or window.

Tooling decisions are inherited from `many-game-show` (see its
ARCHITECTURE.md). App architecture is **not yet decided**.

## Inherited tooling

| Concern | Choice |
|---|---|
| Language | Python 3.13+ |
| Package mgr | uv |
| Lint / format | ruff only (no black) |
| Type check | mypy (strict-ish: `disallow_untyped_defs`) |
| Tests | pytest + pytest-cov |
| CI | GitHub Actions: `lint-and-typecheck`, `tests`, `commit-lint` |

## Deliberately not ported yet

`many-game-show` also uses FastAPI/SQLModel, a vanilla-JS frontend, djlint
and pytest-playwright. Telestration over a window may be a desktop overlay
rather than a web app, so those are added only if the design calls for them.

## Open questions

- Delivery shape: desktop overlay, browser-based, or both?
- Session/turn recording: `scripts/session_timing.py` and `SESSION_LOG.md`
  are ported from `many-game-show`. Is the app itself also meant to record
  sessions/turns (e.g. telestration sessions), or only the dev workflow?
