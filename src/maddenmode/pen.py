"""Pens: color, width, feather and how strokes dissipate."""

import dataclasses
from dataclasses import dataclass
from enum import StrEnum

from maddenmode.palette import PALETTE, PaletteColor

MAX_TIME_S = 10.0


class DissipationMode(StrEnum):
    HOLD = "hold"
    TIMED_FADE = "timed_fade"
    TAIL_FIRST = "tail_first"


def check_time(name: str, value: float) -> None:
    """Dissipation times are variable from 0.0 s to 10.0 s."""
    if not 0.0 <= value <= MAX_TIME_S:
        raise ValueError(f"{name} must be between 0.0 and {MAX_TIME_S}, got {value}")


@dataclass(frozen=True)
class Pen:
    name: str
    color: PaletteColor = PALETTE[0]
    width: float = 12.0
    # Softness as a feather width in pixels on each side of a solid core.
    # 0 is a hard edge.
    feather: float = 2.0
    mode: DissipationMode = DissipationMode.HOLD
    # How long a stroke stays solid before fading starts.
    hold_s: float = 0.0
    # How long the fade takes. 0.0 means no fade at all (the stroke is held).
    fade_s: float = 0.0

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError(f"width must be positive, got {self.width}")
        if self.feather < 0:
            raise ValueError(f"feather must not be negative, got {self.feather}")
        check_time("hold_s", self.hold_s)
        check_time("fade_s", self.fade_s)

    @property
    def dissipates(self) -> bool:
        return self.mode != DissipationMode.HOLD and self.fade_s > 0

    def with_color(self, color: PaletteColor) -> "Pen":
        return dataclasses.replace(self, color=color)


# Placeholder defaults to be tuned by hand once there is a real overlay.
DEFAULT_PENS: tuple[Pen, ...] = (
    Pen("marker", color=PALETTE[1], width=6.0, feather=0.0),
    Pen("highlighter", color=PALETTE[0], width=14.0, feather=2.0),
    Pen(
        "flash",
        color=PALETTE[5],
        width=8.0,
        feather=2.0,
        mode=DissipationMode.TIMED_FADE,
        hold_s=1.0,
        fade_s=2.0,
    ),
    Pen(
        "comet",
        color=PALETTE[3],
        width=24.0,
        feather=2.0,
        mode=DissipationMode.TAIL_FIRST,
        hold_s=1.5,
        fade_s=3.0,
    ),
)
