"""Finding and tracking other applications' windows. No Qt.

A `WindowBackend` does the platform-specific part. Only Windows has a real one
(`gui/windows_win32.py`); everywhere else `NullWindowBackend` reports that
window pinning is unavailable, and monitor targeting still works.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from maddenmode.targeting import Rect

MIN_WINDOW_SIZE = 50  # ignore tiny helper windows


@dataclass(frozen=True)
class WindowInfo:
    handle: int
    title: str
    rect: Rect  # physical pixels


class WindowKind(StrEnum):
    VISIBLE = "visible"
    MINIMIZED = "minimized"  # also used for hidden or cloaked: "not showing now"
    GONE = "gone"


@dataclass(frozen=True)
class WindowState:
    kind: WindowKind
    rect: Rect | None = None  # physical pixels, set when VISIBLE


class WindowBackend(Protocol):
    available: bool

    def list_windows(self) -> list[WindowInfo]:
        """Top-level windows worth offering in a picker."""

    def get_state(self, handle: int) -> WindowState:
        """Current state and rectangle of one window."""


class NullWindowBackend:
    """For platforms without window pinning."""

    available = False

    def list_windows(self) -> list[WindowInfo]:
        return []

    def get_state(self, handle: int) -> WindowState:
        return WindowState(WindowKind.GONE)


def is_pickable(
    *,
    title: str,
    visible: bool,
    minimized: bool,
    cloaked: bool,
    tool_window: bool,
    own_process: bool,
    rect: Rect,
) -> bool:
    """Whether a window should appear in the picker.

    Excludes windows a person would not think of as "a window": hidden or
    cloaked ones, minimized ones, tool windows, tiny ones, untitled ones, and
    our own overlay, toolbar and toast.
    """
    return (
        bool(title.strip())
        and visible
        and not minimized
        and not cloaked
        and not tool_window
        and not own_process
        and rect.width >= MIN_WINDOW_SIZE
        and rect.height >= MIN_WINDOW_SIZE
    )
