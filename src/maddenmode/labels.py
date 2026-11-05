"""Short human-readable descriptions for the UI. No Qt."""

import sys

from maddenmode.pen import DissipationMode, Pen

# A Mac has Control, Option and Command keys. Control and Shift keep their
# names, so "Ctrl+Shift" is the same on every platform; the Alt key is labelled
# Option on a Mac, so that is what is shown there. (How key presses are read on
# a Mac is in gui/keys.py.)
MAC_MODIFIER_NAMES = {"Alt": "Option"}


def is_mac(platform: str = sys.platform) -> bool:
    return platform == "darwin"


def display_chord(chord: str, platform: str = sys.platform) -> str:
    """A key chord or prefix as the user should read it on this platform.

    Unchanged on Windows and Linux. On macOS the Alt key is called Option:
    'Ctrl+Alt+D' is shown as 'Ctrl+Option+D'. Ctrl and Shift are unchanged.
    """
    if not is_mac(platform):
        return chord
    return "+".join(MAC_MODIFIER_NAMES.get(part, part) for part in chord.split("+"))


def mode_label(mode: DissipationMode) -> str:
    return {
        DissipationMode.HOLD: "hold",
        DissipationMode.TIMED_FADE: "timed fade",
        DissipationMode.TAIL_FIRST: "tail-first fade",
    }[mode]


def describe_pen(pen: Pen) -> str:
    """e.g. 'comet · cyan · tail-first fade (hold 0.5 s, fade 1.5 s)'."""
    if pen.dissipates:
        how = f"{mode_label(pen.mode)} (hold {pen.hold_s:g} s, fade {pen.fade_s:g} s)"
    else:
        how = "hold"
    return f"{pen.name} · {pen.color.name} · {how}"
