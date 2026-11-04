"""Opacity of stroke points over time. Pure math, driven by a caller clock."""

from maddenmode.pen import DissipationMode
from maddenmode.stroke import Stroke


def fade_factor(elapsed: float, fade_s: float) -> float:
    """1.0 before the fade starts, falling linearly to 0.0 over fade_s.

    A fade_s of 0 means the fade is instant once it has started.
    """
    if elapsed < 0:
        return 1.0
    if fade_s <= 0:
        return 0.0
    return max(0.0, 1.0 - elapsed / fade_s)


def _clear_factor(stroke: Stroke, now: float) -> float:
    if stroke.cleared_at is None:
        return 1.0
    return fade_factor(now - stroke.cleared_at, stroke.clear_fade_s)


def point_opacity(stroke: Stroke, index: int, now: float) -> float:
    """Opacity (0.0 to 1.0) of one point of a stroke at time `now`."""
    point = stroke.points[index]
    if now < point.t:
        return 0.0  # not drawn yet

    opacity = 1.0
    pen = stroke.pen
    if pen.dissipates:
        if pen.mode == DissipationMode.TIMED_FADE:
            # The whole stroke fades together, counted from pen lift.
            if stroke.pen_up_at is not None:
                opacity = fade_factor(now - stroke.pen_up_at - pen.hold_s, pen.fade_s)
        elif pen.mode == DissipationMode.TAIL_FIRST:
            # Each point fades on its own, counted from when it was drawn.
            opacity = fade_factor(now - point.t - pen.hold_s, pen.fade_s)

    return opacity * _clear_factor(stroke, now)


def is_expired(stroke: Stroke, now: float) -> bool:
    """True once nothing of the stroke is visible and it can be dropped."""
    if stroke.cleared_at is not None and now >= stroke.cleared_at:
        if _clear_factor(stroke, now) <= 0.0:
            return True
    if not stroke.finished:
        return False  # still being drawn
    return all(point_opacity(stroke, i, now) <= 0.0 for i in range(len(stroke.points)))
