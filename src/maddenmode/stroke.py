"""Strokes: a pen plus the timestamped points drawn with it."""

from dataclasses import dataclass, field

from maddenmode.pen import Pen


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    t: float  # seconds, on whatever clock the caller uses
    # Reserved for stylus pressure. Always 1.0 until pressure is supported,
    # so the stroke format will not change when it is.
    pressure: float = 1.0


@dataclass
class Stroke:
    pen: Pen
    points: list[Point] = field(default_factory=list)
    pen_up_at: float | None = None
    # Set by the scene when "fade all" is triggered for this stroke.
    cleared_at: float | None = None
    clear_fade_s: float = 0.0

    def add_point(self, x: float, y: float, t: float, pressure: float = 1.0) -> None:
        self.points.append(Point(x, y, t, pressure))

    def lift(self, t: float) -> None:
        if self.pen_up_at is None:
            self.pen_up_at = t

    @property
    def finished(self) -> bool:
        return self.pen_up_at is not None
