from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from maddenmode.controller import Controller
from maddenmode.gui.toast import Toast
from maddenmode.labels import describe_pen
from maddenmode.scene import Scene


def make() -> tuple[Toast, Controller]:
    controller = Controller(Scene())
    return Toast(controller), controller


def test_is_click_through_and_never_takes_focus(qapp: QApplication) -> None:
    toast, _ = make()
    flags = toast.windowFlags()
    assert flags & Qt.WindowType.WindowTransparentForInput
    assert flags & Qt.WindowType.WindowDoesNotAcceptFocus


def test_says_when_draw_mode_changes(qapp: QApplication) -> None:
    toast, controller = make()
    controller.toggle_draw(0.0)
    assert toast.text == "Draw mode ON"
    assert toast.isVisible()
    controller.toggle_draw(1.0)
    assert toast.text == "Draw mode OFF"
    toast.close()


def test_describes_the_pen_when_it_changes(qapp: QApplication) -> None:
    toast, controller = make()
    controller.next_pen()
    assert toast.text == describe_pen(controller.current_pen)
    toast.close()


def test_describes_the_pen_when_the_color_changes(qapp: QApplication) -> None:
    toast, controller = make()
    controller.select_color(5)
    assert "magenta" in toast.text
    toast.close()


def test_says_nothing_for_unrelated_changes(qapp: QApplication) -> None:
    toast, controller = make()
    controller.toggle_toolbar()
    assert toast.text == ""
    assert not toast.isVisible()


def test_is_sized_to_its_text_and_hides(qapp: QApplication) -> None:
    toast, _ = make()
    toast.show_message("short")
    narrow = toast.width()
    toast.show_message("a much longer message than the short one")
    assert toast.width() > narrow
    assert toast._hold.isActive()
    toast._hide_now()
    assert not toast.isVisible()
    assert not toast._hold.isActive()


def test_fade_starts_after_the_hold_time(qapp: QApplication) -> None:
    toast, _ = make()
    toast.show_message("hello")
    toast._start_fade()
    assert toast._fade.state().name == "Running"
    toast._hide_now()


def test_paints_text_over_a_background(qapp: QApplication) -> None:
    toast, _ = make()
    toast.show_message("paint me")
    image = toast.grab().toImage()
    assert image.width() == toast.width()
    assert any(
        image.pixelColor(x, image.height() // 2).alpha() > 0
        for x in range(image.width())
    )
    toast._hide_now()
