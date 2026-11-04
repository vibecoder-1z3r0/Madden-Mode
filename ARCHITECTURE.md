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

## Product decisions so far

- Madden Mode is **telestration**: freehand marks drawn over live content.
- Two modes sharing one stroke engine (pen/arrow tools, fade-out, stroke
  recording):
  - **Overlay mode (build and test first):** transparent, always-on-top layer
    drawn over any window, app or fullscreen game; click-through when not
    drawing.
  - **Studio mode (tabled):** a "live feed" of the screen with pause, rewind
    and fast forward, then telestrate over the paused frame. Requires a
    rolling capture buffer.
- **Overlay mode keeps no history.** Strokes are ephemeral. Persisted strokes
  and a timeline showing them are a studio-mode idea only.
- **Pens** (draft): color, width, hardness/softness and dissipation.
  - Colors: keep simple (small fixed palette).
  - Hardness/softness: supported.
  - Pressure-sensitive width: wanted, but deferred (hard to test). Strokes
    carry a per-point pressure field defaulting to 1.0 so it can be added
    later without changing the stroke format.
  - Dissipation: all three modes, set per pen, **hold is the default**:
    - hold: stays until cleared
    - timed fade: whole stroke fades after N seconds
    - tail-first fade: oldest part of the line fades first
- **First target: Windows, windowed/borderless windows.** True fullscreen
  (exclusive) games are best-effort and later. macOS and Linux come after.
- No browser UI.

## Open questions

- Delivery shape: desktop overlay, browser-based, or both?
- Session/turn recording: `scripts/session_timing.py` and `SESSION_LOG.md`
  are ported from `many-game-show`. Is the app itself also meant to record
  sessions/turns (e.g. telestration sessions), or only the dev workflow?
