"""Where the overlay draws: a monitor, or a pinned window. No Qt, so testable.

Coordinate systems
------------------
Windows reports window rectangles in *physical* pixels. Qt places widgets in
*logical* (device-independent) pixels. `physical_to_logical` converts between
them using each screen's device pixel ratio.

ASSUMPTION (not verified on a real multi-monitor, mixed-scaling setup): Qt
keeps each screen's top-left at its native position and scales only its size,
so a point on a screen maps as
    logical = screen_origin + (physical - screen_origin) / dpr
At a device pixel ratio of 1 (the common case) this is exact.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def center(self) -> tuple[float, float]:
        return self.x + self.width / 2, self.y + self.height / 2

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px < self.right and self.y <= py < self.bottom


@dataclass(frozen=True)
class ScreenInfo:
    index: int
    name: str
    geometry: Rect  # logical pixels
    dpr: float = 1.0
    primary: bool = False

    @property
    def native_rect(self) -> Rect:
        """The screen's rectangle in physical pixels."""
        g = self.geometry
        return Rect(g.x, g.y, round(g.width * self.dpr), round(g.height * self.dpr))

    def label(self) -> str:
        native = self.native_rect
        size = f"{native.width}x{native.height}"
        primary = ", primary" if self.primary else ""
        return f"Monitor {self.index + 1}: {self.name} ({size}{primary})"


@dataclass(frozen=True)
class MonitorTarget:
    index: int = 0


@dataclass(frozen=True)
class WindowTarget:
    handle: int
    title: str


Target = MonitorTarget | WindowTarget


def resolve_monitor(index: int, screens: list[ScreenInfo]) -> tuple[ScreenInfo, bool]:
    """The screen for `index`, and whether we had to fall back to the primary.

    A saved monitor can be unplugged later, so a missing index is not an error.
    """
    if not screens:
        raise ValueError("no screens available")
    if 0 <= index < len(screens):
        return screens[index], False
    primary = next((s for s in screens if s.primary), screens[0])
    return primary, True


def physical_to_logical(rect: Rect, screens: list[ScreenInfo]) -> Rect:
    """Convert a rectangle in physical pixels to Qt's logical pixels."""
    if not screens:
        raise ValueError("no screens available")
    cx, cy = rect.center
    screen = next(
        (s for s in screens if s.native_rect.contains(cx, cy)),
        None,
    )
    if screen is None:  # off every screen: use the nearest screen's scaling
        screen = min(
            screens,
            key=lambda s: (
                (s.native_rect.center[0] - cx) ** 2
                + (s.native_rect.center[1] - cy) ** 2
            ),
        )
    ox, oy = screen.geometry.x, screen.geometry.y
    dpr = screen.dpr
    return Rect(
        ox + round((rect.x - ox) / dpr),
        oy + round((rect.y - oy) / dpr),
        max(1, round(rect.width / dpr)),
        max(1, round(rect.height / dpr)),
    )


def describe_target(target: Target, screens: list[ScreenInfo]) -> str:
    if isinstance(target, WindowTarget):
        return f"Window: {target.title}"
    screen, fell_back = resolve_monitor(target.index, screens)
    suffix = " (fallback)" if fell_back else ""
    return f"Monitor {screen.index + 1}{suffix}"
