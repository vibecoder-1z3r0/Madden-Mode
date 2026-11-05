"""Draw-mode and hotkey logic. No GUI imports, so it is fully testable."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from maddenmode.palette import PALETTE
from maddenmode.pen import DEFAULT_PENS, Pen, check_time
from maddenmode.scene import Scene
from maddenmode.stroke import Stroke
from maddenmode.targeting import MonitorTarget, Target


class ModifierPrefix(StrEnum):
    CTRL_SHIFT = "Ctrl+Shift"
    CTRL_ALT = "Ctrl+Alt"


class Action(StrEnum):
    TOGGLE_DRAW = "toggle_draw"
    CLEAR_ALL = "clear_all"
    FADE_ALL = "fade_all"
    NEXT_PEN = "next_pen"
    PREV_PEN = "prev_pen"
    EXIT_DRAW = "exit_draw"
    TOGGLE_TOOLBAR = "toggle_toolbar"


# Global keys, active over the game. The modifier prefix is a setting.
GLOBAL_KEYS: dict[str, Action] = {
    "D": Action.TOGGLE_DRAW,
    "C": Action.CLEAR_ALL,
    "F": Action.FADE_ALL,
    "H": Action.TOGGLE_TOOLBAR,
}

# Draw-mode keys. The overlay owns the keyboard while drawing, so these are
# plain keys. "1" to "8" pick a color and are handled separately.
DRAW_MODE_KEYS: dict[str, Action] = {
    "]": Action.NEXT_PEN,
    "[": Action.PREV_PEN,
    "Esc": Action.EXIT_DRAW,
}


@dataclass
class Settings:
    prefix: ModifierPrefix = ModifierPrefix.CTRL_SHIFT
    # When True, draw mode is on only while the toggle key is held.
    hold_to_draw: bool = False
    # How long "fade all" takes, 0.0 to 10.0 s (0.0 is instant).
    fade_all_s: float = 1.5
    # Which monitor to draw over (0 is the first/primary screen). A pinned
    # window is not saved: window handles do not survive a restart.
    monitor: int = 0

    def __post_init__(self) -> None:
        check_time("fade_all_s", self.fade_all_s)
        if self.monitor < 0:
            raise ValueError(f"monitor must not be negative, got {self.monitor}")


def global_bindings(prefix: ModifierPrefix) -> dict[str, Action]:
    return {f"{prefix}+{key}": action for key, action in GLOBAL_KEYS.items()}


def normalize_key(key: str) -> str:
    """Make single letters in a chord upper case, e.g. 'ctrl+shift+d'."""
    parts = [p.strip() for p in key.split("+")]
    out = []
    for i, part in enumerate(parts):
        if i < len(parts) - 1:
            out.append(part.capitalize())  # modifiers: Ctrl, Shift, Alt
        elif len(part) == 1:
            out.append(part.upper())
        else:
            out.append(part.capitalize() if part.lower() == "esc" else part)
    return "+".join(out)


class Controller:
    def __init__(
        self,
        scene: Scene,
        pens: tuple[Pen, ...] = DEFAULT_PENS,
        settings: Settings | None = None,
    ) -> None:
        if not pens:
            raise ValueError("at least one pen is required")
        self.scene = scene
        self.pens = pens
        self.settings = settings or Settings()
        self.draw_mode = False
        self.pen_index = 0
        # None means "use each pen's own color" until a color is picked.
        self.color_index: int | None = None
        self.active_stroke: Stroke | None = None
        # Called with the new value whenever draw mode actually changes, so a
        # window can switch between click-through and drawing.
        self.on_draw_mode_changed: Callable[[bool], None] | None = None
        # Whether the on-screen toolbar should be showing (hotkey toggles it).
        self.toolbar_visible = True
        # Where the overlay draws: a monitor, or a pinned window.
        self.target: Target = MonitorTarget(self.settings.monitor)
        self._listeners: list[Callable[[], None]] = []

    @property
    def current_pen(self) -> Pen:
        pen = self.pens[self.pen_index]
        if self.color_index is not None:
            pen = pen.with_color(PALETTE[self.color_index])
        return pen

    # -- change notification ---------------------------------------------

    def add_listener(self, listener: Callable[[], None]) -> None:
        """Call `listener` whenever draw mode, pen, color, toolbar visibility
        or settings change, so UI can redraw itself from the controller."""
        self._listeners.append(listener)

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    # -- actions (shared by hotkeys, toolbar and tray) -----------------------

    def toggle_draw(self, now: float) -> None:
        if self.settings.hold_to_draw:
            self._set_draw_mode(True, now)
        else:
            self._set_draw_mode(not self.draw_mode, now)

    def set_draw_mode(self, on: bool, now: float) -> None:
        self._set_draw_mode(on, now)

    def select_color(self, index: int) -> None:
        if not 0 <= index < len(PALETTE):
            raise ValueError(f"color index out of range: {index}")
        self.color_index = index
        self._notify()

    def select_pen(self, index: int) -> None:
        if not 0 <= index < len(self.pens):
            raise ValueError(f"pen index out of range: {index}")
        self.pen_index = index
        self._notify()

    def next_pen(self) -> None:
        self.select_pen((self.pen_index + 1) % len(self.pens))

    def prev_pen(self) -> None:
        self.select_pen((self.pen_index - 1) % len(self.pens))

    def clear_all(self) -> None:
        self.active_stroke = None
        self.scene.clear_all()

    def fade_all(self, now: float) -> None:
        self.scene.fade_all(now, self.settings.fade_all_s)

    def set_target(self, target: Target) -> None:
        self.target = target
        self._notify()

    def toggle_toolbar(self) -> None:
        self.toolbar_visible = not self.toolbar_visible
        self._notify()

    def apply_settings(self, settings: Settings, pens: tuple[Pen, ...]) -> None:
        """Replace settings and pens (e.g. from the settings dialog)."""
        if not pens:
            raise ValueError("at least one pen is required")
        self.settings = settings
        self.pens = pens
        self.pen_index = min(self.pen_index, len(pens) - 1)
        if isinstance(self.target, MonitorTarget):
            # a pinned window stays pinned; a monitor choice follows the setting
            self.target = MonitorTarget(settings.monitor)
        self._notify()

    # -- keyboard ---------------------------------------------------------

    def press(self, key: str, now: float) -> bool:
        """Handle a key press. Returns True if the overlay consumed it."""
        key = normalize_key(key)
        action = global_bindings(self.settings.prefix).get(key)
        if action is not None:
            self._run(action, now)
            return True
        if not self.draw_mode:
            return False  # not drawing: every other key belongs to the game
        if key in {str(n) for n in range(1, len(PALETTE) + 1)}:
            self.select_color(int(key) - 1)
            return True
        action = DRAW_MODE_KEYS.get(key)
        if action is not None:
            self._run(action, now)
            return True
        return False

    def release(self, key: str, now: float) -> bool:
        """Handle a key release. Only matters for hold-to-draw."""
        if not self.settings.hold_to_draw:
            return False
        key = normalize_key(key)
        action = global_bindings(self.settings.prefix).get(key)
        if action == Action.TOGGLE_DRAW:
            self._set_draw_mode(False, now)
            return True
        return False

    def _run(self, action: Action, now: float) -> None:
        if action == Action.TOGGLE_DRAW:
            self.toggle_draw(now)
        elif action == Action.EXIT_DRAW:
            self._set_draw_mode(False, now)
        elif action == Action.CLEAR_ALL:
            self.clear_all()
        elif action == Action.FADE_ALL:
            self.fade_all(now)
        elif action == Action.NEXT_PEN:
            self.next_pen()
        elif action == Action.PREV_PEN:
            self.prev_pen()
        elif action == Action.TOGGLE_TOOLBAR:
            self.toggle_toolbar()

    def _set_draw_mode(self, on: bool, now: float) -> None:
        if self.draw_mode and not on:
            self.pointer_up(now)  # never leave a stroke dangling
        changed = self.draw_mode != on
        self.draw_mode = on
        if changed:
            if self.on_draw_mode_changed is not None:
                self.on_draw_mode_changed(on)
            self._notify()

    # -- pointer ----------------------------------------------------------

    def pointer_down(
        self, x: float, y: float, now: float, pressure: float = 1.0
    ) -> bool:
        """Start a stroke. Ignored (returns False) outside draw mode."""
        if not self.draw_mode:
            return False
        self.pointer_up(now)
        self.active_stroke = self.scene.begin_stroke(
            self.current_pen, x, y, now, pressure
        )
        return True

    def pointer_move(
        self, x: float, y: float, now: float, pressure: float = 1.0
    ) -> None:
        if self.active_stroke is not None:
            self.active_stroke.add_point(x, y, now, pressure)

    def pointer_up(self, now: float) -> None:
        if self.active_stroke is not None:
            self.active_stroke.lift(now)
            self.active_stroke = None
