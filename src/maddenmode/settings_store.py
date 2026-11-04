"""Load and save settings and pens as JSON. No Qt, so it is fully testable.

A bad or missing file never stops the app: loading falls back to defaults and
reports what went wrong, so the UI can tell the user instead of crashing.
"""

import json
import os
from pathlib import Path
from typing import Any

from maddenmode.controller import ModifierPrefix, Settings
from maddenmode.palette import PALETTE
from maddenmode.pen import DEFAULT_PENS, DissipationMode, Pen

SCHEMA_VERSION = 1


def default_path() -> Path:
    """Per-user settings file location for this platform."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "madden-mode" / "settings.json"


def pen_to_dict(pen: Pen) -> dict[str, Any]:
    return {
        "name": pen.name,
        "color": pen.color.name,
        "width": pen.width,
        "feather": pen.feather,
        "mode": pen.mode.value,
        "hold_s": pen.hold_s,
        "fade_s": pen.fade_s,
    }


def pen_from_dict(data: dict[str, Any]) -> Pen:
    colors = {c.name: c for c in PALETTE}
    color = colors[data["color"]]  # KeyError -> caught by load()
    return Pen(
        name=str(data["name"]),
        color=color,
        width=float(data["width"]),
        feather=float(data["feather"]),
        mode=DissipationMode(data["mode"]),
        hold_s=float(data["hold_s"]),
        fade_s=float(data["fade_s"]),
    )


def to_dict(settings: Settings, pens: tuple[Pen, ...]) -> dict[str, Any]:
    return {
        "version": SCHEMA_VERSION,
        "prefix": settings.prefix.value,
        "hold_to_draw": settings.hold_to_draw,
        "fade_all_s": settings.fade_all_s,
        "pens": [pen_to_dict(p) for p in pens],
    }


def from_dict(data: dict[str, Any]) -> tuple[Settings, tuple[Pen, ...]]:
    settings = Settings(
        prefix=ModifierPrefix(data["prefix"]),
        hold_to_draw=bool(data["hold_to_draw"]),
        fade_all_s=float(data["fade_all_s"]),
    )
    pens = tuple(pen_from_dict(p) for p in data["pens"])
    if not pens:
        raise ValueError("no pens in settings")
    return settings, pens


def save(path: Path, settings: Settings, pens: tuple[Pen, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_dict(settings, pens), indent=2) + "\n")


def load(path: Path) -> tuple[Settings, tuple[Pen, ...], str | None]:
    """Return (settings, pens, warning). A missing file is not a problem.

    On any problem with the file the defaults are returned together with a
    short human-readable warning.
    """
    if not path.exists():
        return Settings(), DEFAULT_PENS, None
    try:
        settings, pens = from_dict(json.loads(path.read_text()))
    except (OSError, ValueError, KeyError, TypeError) as err:
        # json.JSONDecodeError and the validation errors are ValueErrors
        return Settings(), DEFAULT_PENS, f"Could not read {path.name}: {err!r}"
    return settings, pens, None
