"""The fixed 8-color pen palette (see ARCHITECTURE.md)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PaletteColor:
    name: str
    hex: str

    @property
    def rgb(self) -> tuple[int, int, int]:
        h = self.hex.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


PALETTE: tuple[PaletteColor, ...] = (
    PaletteColor("yellow", "#FFE600"),
    PaletteColor("red", "#FF2D2D"),
    PaletteColor("white", "#FFFFFF"),
    PaletteColor("cyan", "#00E5FF"),
    PaletteColor("orange", "#FF8A00"),
    PaletteColor("magenta", "#FF3DCB"),
    PaletteColor("blue", "#3D7BFF"),
    PaletteColor("black", "#111111"),
)
