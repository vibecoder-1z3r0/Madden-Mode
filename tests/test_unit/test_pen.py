import pytest

from maddenmode.palette import PALETTE
from maddenmode.pen import DEFAULT_PENS, DissipationMode, Pen


def test_palette_has_eight_unique_colors() -> None:
    assert len(PALETTE) == 8
    assert len({c.hex for c in PALETTE}) == 8
    assert "green" not in {c.name for c in PALETTE}


def test_palette_rgb() -> None:
    assert PALETTE[2].name == "white"
    assert PALETTE[2].rgb == (255, 255, 255)
    assert PALETTE[0].rgb == (0xFF, 0xE6, 0x00)


def test_pen_defaults_hold_and_do_not_dissipate() -> None:
    pen = Pen("p")
    assert pen.mode == DissipationMode.HOLD
    assert pen.feather == 2.0
    assert not pen.dissipates


@pytest.mark.parametrize("bad", [-0.1, 10.1])
def test_times_must_be_between_0_and_10(bad: float) -> None:
    with pytest.raises(ValueError):
        Pen("p", hold_s=bad)
    with pytest.raises(ValueError):
        Pen("p", fade_s=bad)


@pytest.mark.parametrize("ok", [0.0, 10.0])
def test_time_limits_are_inclusive(ok: float) -> None:
    Pen("p", hold_s=ok, fade_s=ok)


def test_width_and_feather_validation() -> None:
    with pytest.raises(ValueError):
        Pen("p", width=0)
    with pytest.raises(ValueError):
        Pen("p", feather=-1)
    Pen("p", feather=0)  # hard edge is allowed


def test_zero_fade_means_no_dissipation_in_any_mode() -> None:
    for mode in DissipationMode:
        assert not Pen("p", mode=mode, hold_s=3.0, fade_s=0.0).dissipates


def test_fade_modes_dissipate_when_fade_is_set() -> None:
    assert Pen("p", mode=DissipationMode.TIMED_FADE, fade_s=1.0).dissipates
    assert Pen("p", mode=DissipationMode.TAIL_FIRST, fade_s=1.0).dissipates
    assert not Pen("p", mode=DissipationMode.HOLD, fade_s=1.0).dissipates


def test_with_color_returns_new_pen() -> None:
    pen = Pen("p")
    other = pen.with_color(PALETTE[3])
    assert other.color == PALETTE[3]
    assert pen.color == PALETTE[0]
    assert other.name == pen.name


def test_default_pens_cover_all_modes() -> None:
    assert {p.mode for p in DEFAULT_PENS} == set(DissipationMode)
