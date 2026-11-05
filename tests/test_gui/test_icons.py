import sys

import pytest
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from maddenmode.gui.icons import (
    APP_ID,
    SIZES,
    SWOOSH,
    app_icon,
    draw_icon,
    make_icon,
    set_app_identity,
)

RED = QColor(255, 0, 0)


def image(size: int, color: QColor | None = None, drawing: bool = False):  # type: ignore[no-untyped-def]
    return draw_icon(size, color, drawing).toImage()


@pytest.mark.parametrize("size", SIZES)
def test_every_size_is_drawn_at_exactly_that_size(
    qapp: QApplication, size: int
) -> None:
    pixmap = draw_icon(size)
    assert (pixmap.width(), pixmap.height()) == (size, size)


@pytest.mark.parametrize("size", SIZES)
def test_the_corner_is_transparent_and_the_tile_is_solid(
    qapp: QApplication, size: int
) -> None:
    img = image(size)
    assert img.pixelColor(0, 0).alpha() == 0  # rounded corner
    # the dark tile, away from the swoosh and corners
    assert img.pixelColor(size // 8, size - size // 8).alpha() == 255


@pytest.mark.parametrize("size", SIZES)
def test_something_bright_is_drawn_so_it_is_not_a_blank_square(
    qapp: QApplication, size: int
) -> None:
    img = image(size)
    bright = sum(
        1
        for x in range(size)
        for y in range(size)
        if img.pixelColor(x, y).blue() > 200 and img.pixelColor(x, y).alpha() == 255
    )
    assert bright >= size  # the swoosh crosses the whole icon


def test_the_swoosh_has_the_brand_color(qapp: QApplication) -> None:
    img = image(256)
    colors = {
        (
            img.pixelColor(x, y).red(),
            img.pixelColor(x, y).green(),
            img.pixelColor(x, y).blue(),
        )
        for x in range(256)
        for y in range(256)
    }
    assert (SWOOSH.red(), SWOOSH.green(), SWOOSH.blue()) in colors


def test_the_pen_color_dot_only_appears_when_given(qapp: QApplication) -> None:
    plain = image(64)
    with_dot = image(64, RED)
    assert plain.pixelColor(46, 46).red() < 80
    dot = with_dot.pixelColor(46, 46)
    assert (dot.red(), dot.green(), dot.blue()) == (255, 0, 0)


def test_the_dot_is_visible_even_at_the_smallest_size(qapp: QApplication) -> None:
    dot = image(16, RED).pixelColor(11, 11)
    assert dot.red() > 200
    assert dot.green() < 60


def test_the_drawing_ring_is_white_and_absent_when_idle(qapp: QApplication) -> None:
    assert image(64, RED, drawing=False).pixelColor(32, 3).red() < 80
    ring = image(64, RED, drawing=True).pixelColor(32, 3)
    assert (ring.red(), ring.green(), ring.blue()) == (255, 255, 255)


def test_the_icon_holds_every_size(qapp: QApplication) -> None:
    sizes = {s.width() for s in make_icon(RED).availableSizes()}
    assert sizes == set(SIZES)


def test_the_app_icon_is_not_null_and_has_no_dot(qapp: QApplication) -> None:
    icon = app_icon()
    assert not icon.isNull()
    assert icon.pixmap(64, 64).toImage().pixelColor(46, 46).red() < 80


def test_set_app_identity_names_the_app_and_gives_it_an_icon(
    qapp: QApplication,
) -> None:
    set_app_identity(qapp)
    assert qapp.applicationName() == "Madden Mode"
    assert qapp.applicationDisplayName() == "Madden Mode"
    assert not qapp.windowIcon().isNull()


def test_the_windows_app_id_is_stable_and_not_python(qapp: QApplication) -> None:
    assert APP_ID == "MaddenMode.Overlay"
    set_app_identity(qapp)  # must not raise on any platform
    assert sys.platform  # (the Win32 call is cosmetic and guarded)
