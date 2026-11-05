"""Short human-readable descriptions for the UI. No Qt."""

import sys

from maddenmode.pen import DissipationMode, Pen

# On macOS the key that Qt calls "Control" is the Command key, and "Alt" is
# Option. Internally the key names stay "Ctrl" and "Alt" everywhere (Qt reports
# Command presses as its Control modifier), so these names are only for showing
# to the user.
MAC_MODIFIER_NAMES = {"Ctrl": "Cmd", "Alt": "Option"}


def is_mac(platform: str = sys.platform) -> bool:
    return platform == "darwin"


def display_chord(chord: str, platform: str = sys.platform) -> str:
    """A key chord or prefix as the user should read it on this platform.

    'Ctrl+Shift+D' stays as it is on Windows and Linux and becomes
    'Cmd+Shift+D' on macOS; 'Ctrl+Alt' becomes 'Cmd+Option'.
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
