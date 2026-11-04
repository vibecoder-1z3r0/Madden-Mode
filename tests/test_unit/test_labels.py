from maddenmode.labels import describe_pen, mode_label
from maddenmode.palette import PALETTE
from maddenmode.pen import DissipationMode, Pen


def test_mode_labels_cover_every_mode() -> None:
    assert {mode_label(m) for m in DissipationMode} == {
        "hold",
        "timed fade",
        "tail-first fade",
    }


def test_describe_a_held_pen() -> None:
    assert describe_pen(Pen("marker", color=PALETTE[1])) == "marker · red · hold"


def test_describe_a_fading_pen_includes_the_times() -> None:
    pen = Pen(
        "comet",
        color=PALETTE[3],
        mode=DissipationMode.TAIL_FIRST,
        hold_s=0.5,
        fade_s=1.5,
    )
    assert (
        describe_pen(pen) == "comet · cyan · tail-first fade (hold 0.5 s, fade 1.5 s)"
    )


def test_zero_fade_is_described_as_hold() -> None:
    pen = Pen("p", mode=DissipationMode.TIMED_FADE, hold_s=2, fade_s=0)
    assert describe_pen(pen).endswith("· hold")
