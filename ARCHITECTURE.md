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
| GUI toolkit | PySide6 (Qt 6) |
| CI | GitHub Actions: `lint-and-typecheck`, `tests`, `commit-lint` |

## Deliberately not ported

`many-game-show` also uses FastAPI/SQLModel, a vanilla-JS frontend, djlint
and pytest-playwright. Madden Mode is a desktop overlay with no browser UI,
so those are not used.

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
  - Hardness/softness: supported as a single **feather width in pixels**
    (0 = hard edge), not a hard/soft switch. The feather is added on each
    side of a solid core, so total width and color stay constant as it
    changes. Default highlighter: **12-16 px wide with a 2 px feather**
    (picked from mock-ups; a wider or blurrier stroke looked too soft).
  - Pressure-sensitive width: wanted, but deferred (hard to test). Strokes
    carry a per-point pressure field defaulting to 1.0 so it can be added
    later without changing the stroke format.
  - Dissipation: all three modes, set per pen, **hold is the default**:
    - hold: stays until cleared
    - timed fade: whole stroke fades after N seconds
    - tail-first fade: oldest part of the line fades first
  - Dissipation uses **two numbers per pen**, each variable from **0.0 s to
    10.0 s**:
    - `hold_s`: how long the stroke stays solid before fading starts.
    - `fade_s`: how long the fade takes. **`fade_s = 0.0` means no fade or
      dissipation** (the stroke is held, whatever `hold_s` is).
  - Timed fade measures `hold_s` from pen lift. Tail-first fade applies the
    same two numbers per point, measured from when each point was drawn
    (assumed; confirm).
- **First target: Windows, windowed/borderless windows.** True fullscreen
  (exclusive) games are best-effort and later. macOS and Linux come after.
- **Language and toolkit: Python 3.13 + PySide6 (Qt 6).** Chosen over
  C++/Qt, Rust, C#, and raw OpenGL for iteration speed and because the logic
  is pure Python and testable in CI. Revisit if studio-mode screen capture
  drops frames (move just that piece native) or if a single-exe installer
  becomes important.
  - Strokes, pens, dissipation math and mode logic stay free of GUI imports
    so the window layer is thin and the core could be ported later.
  - Licensing: PySide6 is LGPL v3 (not PyQt6, which is GPL/commercial). Fine
    for MIT source distribution via pip/uv. If we ever bundle an installer
    (PyInstaller etc.), add Qt LGPL notices and keep Qt as separate libraries.
- No browser UI.

## Open questions

- Delivery shape: desktop overlay, browser-based, or both?
- Session/turn recording: `scripts/session_timing.py` and `SESSION_LOG.md`
  are ported from `many-game-show`. Is the app itself also meant to record
  sessions/turns (e.g. telestration sessions), or only the dev workflow?
