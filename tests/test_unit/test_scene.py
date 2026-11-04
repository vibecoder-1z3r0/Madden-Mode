import pytest

from maddenmode.pen import DissipationMode, Pen
from maddenmode.scene import Scene

HELD = Pen("held")
TIMED = Pen("timed", mode=DissipationMode.TIMED_FADE, hold_s=0.0, fade_s=1.0)


def test_begin_stroke_adds_first_point() -> None:
    scene = Scene()
    stroke = scene.begin_stroke(HELD, 5.0, 6.0, 0.25)
    assert scene.strokes == [stroke]
    assert stroke.points[0].x == 5.0
    assert stroke.points[0].pressure == 1.0


def test_clear_all_removes_everything_instantly() -> None:
    scene = Scene()
    scene.begin_stroke(HELD, 0, 0, 0)
    scene.begin_stroke(TIMED, 0, 0, 0)
    scene.clear_all()
    assert scene.strokes == []


def test_fade_all_reaches_held_strokes_too() -> None:
    scene = Scene()
    held = scene.begin_stroke(HELD, 0, 0, 0.0)
    held.lift(0.1)
    scene.fade_all(now=10.0, fade_s=2.0)
    scene.prune(10.5)
    assert scene.strokes == [held]  # still fading
    scene.prune(12.0)
    assert scene.strokes == []


def test_fade_all_does_not_touch_later_strokes() -> None:
    scene = Scene()
    old = scene.begin_stroke(HELD, 0, 0, 0.0)
    old.lift(0.1)
    scene.fade_all(now=1.0, fade_s=0.0)
    new = scene.begin_stroke(HELD, 0, 0, 2.0)
    new.lift(2.1)
    scene.prune(5.0)
    assert scene.strokes == [new]


def test_fade_all_twice_keeps_original_start() -> None:
    scene = Scene()
    stroke = scene.begin_stroke(HELD, 0, 0, 0.0)
    scene.fade_all(now=1.0, fade_s=4.0)
    scene.fade_all(now=3.0, fade_s=1.0)
    assert stroke.cleared_at == 1.0
    assert stroke.clear_fade_s == 4.0


@pytest.mark.parametrize("bad", [-1.0, 10.5])
def test_fade_all_time_is_limited_to_0_to_10(bad: float) -> None:
    with pytest.raises(ValueError):
        Scene().fade_all(0.0, bad)


def test_prune_drops_only_expired_strokes() -> None:
    scene = Scene()
    held = scene.begin_stroke(HELD, 0, 0, 0.0)
    held.lift(0.1)
    timed = scene.begin_stroke(TIMED, 0, 0, 0.0)
    timed.lift(0.1)
    scene.prune(0.5)
    assert len(scene.strokes) == 2
    scene.prune(1.2)
    assert scene.strokes == [held]
