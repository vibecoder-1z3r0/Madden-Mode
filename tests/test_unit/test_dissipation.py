import pytest

from maddenmode.dissipation import fade_factor, is_expired, point_opacity
from maddenmode.pen import DissipationMode, Pen
from maddenmode.stroke import Stroke


def make_stroke(pen: Pen, times: list[float], lift_at: float | None) -> Stroke:
    stroke = Stroke(pen)
    for i, t in enumerate(times):
        stroke.add_point(float(i), 0.0, t)
    if lift_at is not None:
        stroke.lift(lift_at)
    return stroke


def test_fade_factor_shape() -> None:
    assert fade_factor(-1.0, 2.0) == 1.0
    assert fade_factor(0.0, 2.0) == 1.0
    assert fade_factor(1.0, 2.0) == pytest.approx(0.5)
    assert fade_factor(2.0, 2.0) == 0.0
    assert fade_factor(5.0, 2.0) == 0.0


def test_fade_factor_zero_length_is_instant() -> None:
    assert fade_factor(-0.1, 0.0) == 1.0
    assert fade_factor(0.0, 0.0) == 0.0


def test_hold_never_fades() -> None:
    stroke = make_stroke(Pen("p"), [0.0, 0.5], lift_at=1.0)
    for now in (1.0, 100.0, 10_000.0):
        assert point_opacity(stroke, 0, now) == 1.0
    assert not is_expired(stroke, 10_000.0)


def test_point_not_drawn_yet_is_invisible() -> None:
    stroke = make_stroke(Pen("p"), [1.0], lift_at=None)
    assert point_opacity(stroke, 0, 0.5) == 0.0
    assert point_opacity(stroke, 0, 1.0) == 1.0


def test_timed_fade_waits_for_pen_up() -> None:
    pen = Pen("p", mode=DissipationMode.TIMED_FADE, hold_s=1.0, fade_s=2.0)
    stroke = make_stroke(pen, [0.0, 1.0], lift_at=None)
    # Pen still down: nothing fades, however long it takes.
    assert point_opacity(stroke, 0, 50.0) == 1.0
    stroke.lift(60.0)
    # Hold for 1 s after pen up, then fade over 2 s, all points together.
    assert point_opacity(stroke, 0, 60.5) == 1.0
    assert point_opacity(stroke, 0, 61.0) == 1.0
    assert point_opacity(stroke, 0, 62.0) == pytest.approx(0.5)
    assert point_opacity(stroke, 1, 62.0) == pytest.approx(0.5)
    assert point_opacity(stroke, 0, 63.0) == 0.0
    assert is_expired(stroke, 63.0)
    assert not is_expired(stroke, 62.9)


def test_tail_first_fades_oldest_point_first() -> None:
    pen = Pen("p", mode=DissipationMode.TAIL_FIRST, hold_s=0.5, fade_s=1.0)
    stroke = make_stroke(pen, [0.0, 0.5, 1.0], lift_at=None)
    now = 1.0
    old = point_opacity(stroke, 0, now)  # drawn 1.0 s ago: 0.5 s into a 1 s fade
    mid = point_opacity(stroke, 1, now)  # drawn 0.5 s ago: exactly at hold end
    new = point_opacity(stroke, 2, now)  # drawn just now: still in hold
    assert old == pytest.approx(0.5)
    assert mid == pytest.approx(1.0)
    assert new == 1.0
    assert old < mid <= new


def test_tail_first_does_not_expire_while_pen_is_down() -> None:
    pen = Pen("p", mode=DissipationMode.TAIL_FIRST, hold_s=0.0, fade_s=1.0)
    stroke = make_stroke(pen, [0.0], lift_at=None)
    assert point_opacity(stroke, 0, 5.0) == 0.0
    assert not is_expired(stroke, 5.0)
    stroke.lift(5.0)
    assert is_expired(stroke, 5.0)


def test_zero_fade_disables_fading_even_with_hold() -> None:
    pen = Pen("p", mode=DissipationMode.TIMED_FADE, hold_s=2.0, fade_s=0.0)
    stroke = make_stroke(pen, [0.0], lift_at=1.0)
    assert point_opacity(stroke, 0, 1000.0) == 1.0


def test_clear_fade_multiplies_with_pen_fade() -> None:
    pen = Pen("p", mode=DissipationMode.TIMED_FADE, hold_s=0.0, fade_s=4.0)
    stroke = make_stroke(pen, [0.0], lift_at=0.0)
    stroke.cleared_at = 2.0
    stroke.clear_fade_s = 2.0
    # at t=3: 3 s into a 4 s pen fade -> 0.25 left; 1 s into a 2 s clear fade
    # -> 0.5 left; the two multiply
    assert point_opacity(stroke, 0, 3.0) == pytest.approx(0.25 * 0.5)


def test_instant_clear_expires_even_a_held_stroke() -> None:
    stroke = make_stroke(Pen("p"), [0.0], lift_at=None)
    stroke.cleared_at = 4.0
    stroke.clear_fade_s = 0.0
    assert point_opacity(stroke, 0, 3.9) == 1.0
    assert point_opacity(stroke, 0, 4.0) == 0.0
    assert is_expired(stroke, 4.0)


def test_lift_is_idempotent() -> None:
    stroke = make_stroke(Pen("p"), [0.0], lift_at=1.0)
    stroke.lift(9.0)
    assert stroke.pen_up_at == 1.0
