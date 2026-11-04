import json
from pathlib import Path

import pytest

from maddenmode import settings_store
from maddenmode.controller import ModifierPrefix, Settings
from maddenmode.palette import PALETTE
from maddenmode.pen import DEFAULT_PENS, DissipationMode, Pen


def test_missing_file_gives_defaults_without_a_warning(tmp_path: Path) -> None:
    settings, pens, warning = settings_store.load(tmp_path / "nope.json")
    assert settings == Settings()
    assert pens == DEFAULT_PENS
    assert warning is None


def test_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "deep" / "dir" / "settings.json"  # parents are created
    settings = Settings(
        prefix=ModifierPrefix.CTRL_ALT, hold_to_draw=True, fade_all_s=3.5
    )
    pens = (
        Pen("a", color=PALETTE[4], width=9, feather=1.5),
        Pen(
            "b",
            color=PALETTE[7],
            mode=DissipationMode.TAIL_FIRST,
            hold_s=0.25,
            fade_s=9.0,
        ),
    )
    settings_store.save(path, settings, pens)
    got_settings, got_pens, warning = settings_store.load(path)
    assert warning is None
    assert got_settings == settings
    assert got_pens == pens


@pytest.mark.parametrize(
    "content",
    [
        "not json at all",
        "[]",
        "{}",
        json.dumps({"prefix": "Ctrl+Shift"}),
    ],
)
def test_bad_files_fall_back_to_defaults_with_a_warning(
    tmp_path: Path, content: str
) -> None:
    path = tmp_path / "settings.json"
    path.write_text(content)
    settings, pens, warning = settings_store.load(path)
    assert settings == Settings()
    assert pens == DEFAULT_PENS
    assert warning is not None
    assert "settings.json" in warning


def _valid() -> dict:  # type: ignore[type-arg]
    return settings_store.to_dict(Settings(), DEFAULT_PENS)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(prefix="Hyper+Shift"),
        lambda d: d.update(fade_all_s=11),
        lambda d: d.update(pens=[]),
        lambda d: d["pens"][0].update(color="green"),
        lambda d: d["pens"][0].update(mode="sparkle"),
        lambda d: d["pens"][0].update(hold_s=-1),
        lambda d: d["pens"][0].update(width=0),
    ],
)
def test_invalid_values_are_rejected(tmp_path: Path, mutate) -> None:  # type: ignore[no-untyped-def]
    data = _valid()
    mutate(data)
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(data))
    settings, pens, warning = settings_store.load(path)
    assert warning is not None
    assert pens == DEFAULT_PENS


def test_default_path_is_per_user_and_named_madden_mode(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    path = settings_store.default_path()
    assert path.name == "settings.json"
    assert path.parent.name == "madden-mode"
    assert path.is_relative_to(tmp_path)
