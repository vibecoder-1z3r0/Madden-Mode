"""The set of strokes currently on screen."""

from maddenmode.dissipation import is_expired
from maddenmode.pen import Pen, check_time
from maddenmode.stroke import Stroke


class Scene:
    def __init__(self) -> None:
        self.strokes: list[Stroke] = []

    def begin_stroke(
        self, pen: Pen, x: float, y: float, t: float, pressure: float = 1.0
    ) -> Stroke:
        stroke = Stroke(pen)
        stroke.add_point(x, y, t, pressure)
        self.strokes.append(stroke)
        return stroke

    def clear_all(self) -> None:
        """Remove every stroke instantly."""
        self.strokes.clear()

    def fade_all(self, now: float, fade_s: float) -> None:
        """Start fading every stroke on screen, held ones included.

        Strokes drawn after this call are not affected. A stroke that is
        already fading out keeps its original start time.
        """
        check_time("fade_s", fade_s)
        for stroke in self.strokes:
            if stroke.cleared_at is None:
                stroke.cleared_at = now
                stroke.clear_fade_s = fade_s

    def prune(self, now: float) -> None:
        """Drop strokes that are no longer visible."""
        self.strokes = [s for s in self.strokes if not is_expired(s, now)]
