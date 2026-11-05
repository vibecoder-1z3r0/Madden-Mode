import pytest

from maddenmode.targeting import (
    MonitorTarget,
    Rect,
    ScreenInfo,
    WindowTarget,
    describe_target,
    physical_to_logical,
    resolve_monitor,
)

PRIMARY = ScreenInfo(0, "Left", Rect(0, 0, 1920, 1080), 1.0, primary=True)
SECOND = ScreenInfo(1, "Right", Rect(1920, 0, 2560, 1440), 1.0)
# a 4K screen scaled to 150%: 3840x2160 physical = 2560x1440 logical
SCALED = ScreenInfo(1, "Hi-DPI", Rect(1920, 0, 2560, 1440), 1.5)


def test_rect_edges_and_center() -> None:
    r = Rect(10, 20, 100, 50)
    assert (r.right, r.bottom) == (110, 70)
    assert r.center == (60.0, 45.0)
    assert r.contains(10, 20)
    assert not r.contains(110, 20)  # right edge is exclusive
    assert not r.contains(9, 20)


def test_native_rect_scales_the_size_only() -> None:
    assert SCALED.native_rect == Rect(1920, 0, 3840, 2160)
    assert PRIMARY.native_rect == PRIMARY.geometry


def test_screen_label_mentions_primary_and_physical_size() -> None:
    assert PRIMARY.label() == "Monitor 1: Left (1920x1080, primary)"
    assert SCALED.label() == "Monitor 2: Hi-DPI (3840x2160)"


def test_resolve_monitor_by_index() -> None:
    assert resolve_monitor(1, [PRIMARY, SECOND]) == (SECOND, False)
    assert resolve_monitor(0, [PRIMARY, SECOND]) == (PRIMARY, False)


@pytest.mark.parametrize("bad", [2, 7, -1])
def test_a_missing_monitor_falls_back_to_the_primary(bad: int) -> None:
    screen, fell_back = resolve_monitor(bad, [SECOND, PRIMARY])  # primary not first
    assert screen == PRIMARY
    assert fell_back


def test_fallback_without_a_flagged_primary_uses_the_first_screen() -> None:
    unflagged = ScreenInfo(0, "Only", Rect(0, 0, 800, 600))
    assert resolve_monitor(5, [unflagged]) == (unflagged, True)


def test_no_screens_is_an_error() -> None:
    with pytest.raises(ValueError):
        resolve_monitor(0, [])
    with pytest.raises(ValueError):
        physical_to_logical(Rect(0, 0, 10, 10), [])


def test_physical_equals_logical_at_scale_one() -> None:
    rect = Rect(100, 200, 640, 480)
    assert physical_to_logical(rect, [PRIMARY, SECOND]) == rect
    on_second = Rect(2000, 100, 800, 600)
    assert physical_to_logical(on_second, [PRIMARY, SECOND]) == on_second


def test_scaled_screen_divides_offsets_and_size_by_the_ratio() -> None:
    # 300 physical px right of the screen origin, 150% scale -> 200 logical px
    rect = Rect(1920 + 300, 150, 900, 600)
    assert physical_to_logical(rect, [PRIMARY, SCALED]) == Rect(
        1920 + 200, 100, 600, 400
    )


def test_the_screen_is_chosen_by_the_window_center() -> None:
    # mostly on the scaled screen, left edge poking onto the primary
    rect = Rect(1900, 0, 900, 600)
    got = physical_to_logical(rect, [PRIMARY, SCALED])
    assert got.width == 600  # scaled by 1.5: the center is on the second screen


def test_a_window_off_every_screen_uses_the_nearest_screen() -> None:
    far = Rect(9000, 9000, 300, 300)
    got = physical_to_logical(far, [PRIMARY, SCALED])
    assert got.width == 200  # nearest is the scaled screen


def test_logical_size_never_collapses_to_zero() -> None:
    assert physical_to_logical(Rect(0, 0, 1, 1), [SCALED]).width >= 1


def test_describe_targets() -> None:
    assert describe_target(MonitorTarget(0), [PRIMARY, SECOND]) == "Monitor 1"
    assert describe_target(MonitorTarget(1), [PRIMARY, SECOND]) == "Monitor 2"
    assert (
        describe_target(MonitorTarget(9), [PRIMARY, SECOND]) == "Monitor 1 (fallback)"
    )
    assert describe_target(WindowTarget(5, "Game"), [PRIMARY]) == "Window: Game"
