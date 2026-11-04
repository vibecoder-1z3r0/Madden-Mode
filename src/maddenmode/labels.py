"""Short human-readable descriptions for the UI. No Qt."""

from maddenmode.pen import DissipationMode, Pen


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
