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
- **Hotkeys** (two layers; all rebindable in a settings file):
  - Global, active over the game, `Ctrl+Shift` prefix:
    - `Ctrl+Shift+D`: toggle draw mode
    - `Ctrl+Shift+C`: clear all (instant)
    - `Ctrl+Shift+F`: fade all
    - `Ctrl+Shift+X`: show/hide the toolbar
  - Draw mode only (the overlay owns the keyboard, so plain keys are safe):
    - `1` to `8`: pick color
    - `]` / `[`: next / previous pen
    - `Esc`: exit draw mode
  - Draw mode is always visibly indicated (e.g. a thin screen border or a
    pen-color dot at the cursor).
  - Optional hold-to-draw as a setting, so draw mode cannot get stuck on.
  - Design principles: never collide with the game; claim keys only while
    drawing; frequent actions are a single key; always show status; always
    have an obvious way out.
  - A **modifier-prefix setting** switches all global keys between
    `Ctrl+Shift` (default) and `Ctrl+Alt` in one step, for when a game or
    app already uses one of them. Individual keys can still be rebound.
  - Known risk: `Ctrl+Shift` combos are used by some apps (browsers, chat
    and streaming tools), which is why they must be rebindable.
- **On-screen UI (minimal):**
  - Toolbar: small always-on-top window (draw toggle, 8 color swatches, pen
    choice, clear, fade, settings, quit). It is its own window so it stays
    clickable while the overlay is click-through, and it never takes keyboard
    focus. It holds no state; everything is refreshed from the controller.
  - Toast: a brief message when pen, color or draw mode changes.
  - Tray icon: menu mirroring the toolbar, so Quit is always reachable even
    with the toolbar hidden.
  - Settings dialog: hotkey prefix, hold-to-draw, fade-all time and each pen's
    width, feather, mode and times. Saved as JSON per user; a bad file falls
    back to defaults with a visible warning.
- **Where it draws:** a target that is either a **monitor** or a **pinned
  window**.
  - Monitor: any screen, chosen in the "Where to draw" dialog. The choice is
    saved (`monitor` in the settings). A missing monitor falls back to the
    primary one with a message.
  - Pinned window (Windows only for now): the overlay is sized to the window,
    follows it by polling every 100 ms, hides while it is minimized, and falls
    back to the saved monitor if the window closes. A pinned window is not
    saved, because window handles do not survive a restart. Strokes live in
    the overlay's own coordinates, so they move with the window.
  - The window listing sits behind a `WindowBackend` interface; only Windows
    has a real one. The logic (coordinate conversion, which windows to offer,
    following) is plain code with tests; only the Win32 calls are thin.
  - Not built: drawing over a region. See FUTURE_CONSIDERATIONS.md.
- **Freehand only for now.** No shapes (arrows, circles, lines) in the first
  version; those can come later.
- **Pens** (draft): color, width, hardness/softness and dissipation.
  - Colors: a fixed **8-color palette**, cycled with a hotkey (keys TBD):
    yellow `#FFE600`, red `#FF2D2D`, white `#FFFFFF`, cyan `#00E5FF`,
    orange `#FF8A00`, magenta `#FF3DCB`, blue `#3D7BFF`, black `#111111`.
    Chosen for contrast on grass, dark scenes and light backgrounds; no
    green (it vanishes on fields). White vanishes on snow/ice and black on
    dark scenes, which is why there is a palette.
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
- **Global hotkey actions** (affect everything on screen, from every pen,
  including held strokes):
  - **Clear all:** removes every stroke instantly, no timer.
  - **Fade all:** fades every stroke out using one global **fade-all time**
    (0.0 s to 10.0 s; 0.0 s is instant).
  - There is no per-pen "all fade" idle-timer mode; "all fade" is driven by
    the hotkey only.
  - Keys: see Hotkeys below.
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
