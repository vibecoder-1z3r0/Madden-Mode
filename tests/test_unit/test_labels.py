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


# -- how key names are shown on each platform ------------------------------------

import pytest  # noqa: E402

from maddenmode.labels import display_chord, is_mac  # noqa: E402


def test_only_darwin_is_a_mac() -> None:
    assert is_mac("darwin")
    for other in ("win32", "linux", "cygwin", ""):
        assert not is_mac(other)


@pytest.mark.parametrize("platform", ["win32", "linux"])
def test_windows_and_linux_keep_the_key_names_as_they_are(platform: str) -> None:
    assert display_chord("Ctrl+Shift+D", platform) == "Ctrl+Shift+D"
    assert display_chord("Ctrl+Alt", platform) == "Ctrl+Alt"


def test_macos_shows_command_and_option() -> None:
    assert display_chord("Ctrl+Shift+D", "darwin") == "Cmd+Shift+D"
    assert display_chord("Ctrl+Alt+C", "darwin") == "Cmd+Option+C"
    assert display_chord("Ctrl+Shift", "darwin") == "Cmd+Shift"  # a prefix alone
    assert display_chord("Ctrl+Alt", "darwin") == "Cmd+Option"


def test_macos_leaves_everything_else_alone() -> None:
    assert display_chord("Esc", "darwin") == "Esc"
    assert display_chord("]", "darwin") == "]"
    assert display_chord("Shift+X", "darwin") == "Shift+X"
    assert display_chord("", "darwin") == ""


def test_the_default_follows_the_machine_it_runs_on() -> None:
    import sys

    expected = "Cmd+Shift+D" if sys.platform == "darwin" else "Ctrl+Shift+D"
    assert display_chord("Ctrl+Shift+D") == expected
