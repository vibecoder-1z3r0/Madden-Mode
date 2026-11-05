import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from maddenmode.controller import Controller, Settings
from maddenmode.gui.keys import key_string
from maddenmode.gui.overlay import OverlayWindow
from maddenmode.palette import PALETTE
from maddenmode.pen import DissipationMode, Pen
from maddenmode.scene import Scene

CTRL_SHIFT = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
LMB = Qt.MouseButton.LeftButton


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def make(
    settings: Settings | None = None, pens: tuple[Pen, ...] | None = None
) -> tuple[OverlayWindow, Controller, FakeClock]:
    clock = FakeClock()
    controller = (
        Controller(Scene(), pens=pens, settings=settings)
        if pens
        else Controller(Scene(), settings=settings)
    )
    window = OverlayWindow(controller, clock=clock)
    window.resize(300, 200)
    window.show()
    return window, controller, clock


def click_toggle(window: OverlayWindow) -> None:
    QTest.keyClick(window, Qt.Key.Key_D, CTRL_SHIFT)


def has_flag(window: OverlayWindow, flag: Qt.WindowType) -> bool:
    return bool(window.windowFlags() & flag)


def test_starts_click_through_frameless_and_on_top(qapp: QApplication) -> None:
    window, _, _ = make()
    assert has_flag(window, Qt.WindowType.WindowTransparentForInput)
    assert has_flag(window, Qt.WindowType.FramelessWindowHint)
    assert has_flag(window, Qt.WindowType.WindowStaysOnTopHint)
    assert window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    window.close()


def test_draw_mode_toggles_click_through(qapp: QApplication) -> None:
    window, controller, _ = make()
    controller.press("Ctrl+Shift+D", 0.0)
    assert not has_flag(window, Qt.WindowType.WindowTransparentForInput)
    assert window.isVisible()
    controller.press("Esc", 1.0)
    assert has_flag(window, Qt.WindowType.WindowTransparentForInput)
    assert window.isVisible()
    window.close()


def test_hotkey_chord_in_the_window_toggles_draw_mode(qapp: QApplication) -> None:
    window, controller, _ = make()
    click_toggle(window)
    assert controller.draw_mode
    window.close()


def test_mouse_drag_draws_a_stroke_in_draw_mode(qapp: QApplication) -> None:
    window, controller, clock = make()
    click_toggle(window)
    clock.now = 1.0
    QTest.mousePress(window, LMB, pos=QPoint(10, 10))
    clock.now = 1.1
    QTest.mouseMove(window, QPoint(50, 40))
    # QTest.mouseMove sends no button state, so build the drag by hand
    controller.pointer_move(60, 50, 1.2)
    clock.now = 1.3
    QTest.mouseRelease(window, LMB, pos=QPoint(70, 60))
    (stroke,) = controller.scene.strokes
    assert (stroke.points[0].x, stroke.points[0].y) == (10, 10)
    assert len(stroke.points) >= 2
    assert stroke.pen_up_at == 1.3
    window.close()


def test_mouse_does_nothing_when_not_drawing(qapp: QApplication) -> None:
    window, controller, _ = make()
    QTest.mousePress(window, LMB, pos=QPoint(10, 10))
    QTest.mouseRelease(window, LMB, pos=QPoint(10, 10))
    assert controller.scene.strokes == []
    window.close()


def test_right_button_does_not_draw(qapp: QApplication) -> None:
    window, controller, _ = make()
    click_toggle(window)
    QTest.mousePress(window, Qt.MouseButton.RightButton, pos=QPoint(10, 10))
    assert controller.scene.strokes == []
    window.close()


def test_draw_mode_keys_work_in_the_window(qapp: QApplication) -> None:
    window, controller, _ = make()
    click_toggle(window)
    QTest.keyClick(window, Qt.Key.Key_3)
    assert controller.current_pen.color == PALETTE[2]
    QTest.keyClick(window, Qt.Key.Key_BracketRight)
    assert controller.pen_index == 1
    QTest.keyClick(window, Qt.Key.Key_Escape)
    assert not controller.draw_mode
    window.close()


def test_unhandled_keys_are_not_consumed(qapp: QApplication) -> None:
    window, controller, _ = make()
    event = QKeyEvent(
        QKeyEvent.Type.KeyPress, Qt.Key.Key_X, Qt.KeyboardModifier.NoModifier, "x"
    )
    window.keyPressEvent(event)
    assert not controller.draw_mode
    window.close()


def test_hold_to_draw_ends_on_key_release(qapp: QApplication) -> None:
    window, controller, _ = make(Settings(hold_to_draw=True))
    QTest.keyPress(window, Qt.Key.Key_D, CTRL_SHIFT)
    assert controller.draw_mode
    QTest.keyRelease(window, Qt.Key.Key_D, CTRL_SHIFT)
    assert not controller.draw_mode
    window.close()


def test_tick_prunes_faded_strokes(qapp: QApplication) -> None:
    pen = Pen("t", mode=DissipationMode.TIMED_FADE, hold_s=0, fade_s=1)
    window, controller, clock = make(pens=(pen,))
    click_toggle(window)
    clock.now = 0.0
    controller.pointer_down(5, 5, 0.0)
    controller.pointer_up(0.0)
    window.tick()
    assert len(controller.scene.strokes) == 1
    clock.now = 2.0
    window.tick()
    assert controller.scene.strokes == []
    window.close()


def test_paints_strokes_and_the_draw_mode_border(qapp: QApplication) -> None:
    pen = Pen("p", color=PALETTE[1], width=10, feather=0)
    window, controller, clock = make(pens=(pen,))
    click_toggle(window)
    controller.pointer_down(20, 100, 0.0)
    controller.pointer_move(280, 100, 0.1)
    controller.pointer_up(0.2)
    image = window.grab().toImage()
    stroke_px = image.pixelColor(150, 100)
    got = (stroke_px.red(), stroke_px.green(), stroke_px.blue())
    # premultiplied-alpha rounding can be off by one unit per channel
    assert all(abs(a - b) <= 2 for a, b in zip(got, PALETTE[1].rgb, strict=True))
    border_px = image.pixelColor(1, 100)
    assert border_px.alpha() > 0  # indicator visible while drawing
    controller.press("Esc", 1.0)
    image = window.grab().toImage()
    assert image.pixelColor(1, 100).alpha() == 0  # gone when not drawing
    window.close()


def test_start_runs_the_frame_timer(qapp: QApplication) -> None:
    window, _, _ = make()
    window.start()
    assert window._timer.isActive()
    window.close()


@pytest.mark.parametrize(
    ("key", "mods", "expected"),
    [
        (Qt.Key.Key_D, CTRL_SHIFT, "Ctrl+Shift+D"),
        (
            Qt.Key.Key_C,
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier,
            "Ctrl+Alt+C",
        ),
        (Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier, "Esc"),
        (Qt.Key.Key_5, Qt.KeyboardModifier.NoModifier, "5"),
        (Qt.Key.Key_BracketLeft, Qt.KeyboardModifier.NoModifier, "["),
        (Qt.Key.Key_BracketRight, Qt.KeyboardModifier.NoModifier, "]"),
        (Qt.Key.Key_F1, Qt.KeyboardModifier.NoModifier, None),
    ],
)
def test_key_string(
    key: Qt.Key, mods: Qt.KeyboardModifier, expected: str | None, qapp: QApplication
) -> None:
    event = QKeyEvent(QKeyEvent.Type.KeyPress, key, mods)
    assert key_string(event) == expected


def test_while_drawing_every_pixel_catches_clicks_on_windows(
    qapp: QApplication,
) -> None:
    """Windows lets clicks through pixels with alpha 0, so none may be left."""
    window, controller, _ = make()
    click_toggle(window)
    image = window.grab().toImage()
    for x, y in [(30, 100), (150, 100), (270, 40), (150, 190), (20, 20)]:
        assert image.pixelColor(x, y).alpha() >= 1, (x, y)
    window.close()


def test_the_click_catching_fill_is_too_faint_to_see(qapp: QApplication) -> None:
    from maddenmode.gui.overlay import HIT_ALPHA

    window, _, _ = make()
    click_toggle(window)
    image = window.grab().toImage()
    inner = image.pixelColor(150, 100)  # well inside, away from the border
    assert inner.alpha() == HIT_ALPHA
    assert HIT_ALPHA <= 3  # under about 1% of full opacity
    window.close()


def test_when_not_drawing_the_overlay_stays_fully_transparent(
    qapp: QApplication,
) -> None:
    window, controller, _ = make()
    click_toggle(window)
    controller.press("Esc", 1.0)
    image = window.grab().toImage()
    assert image.pixelColor(150, 100).alpha() == 0
    window.close()


def test_strokes_are_drawn_over_the_fill_in_full_color(qapp: QApplication) -> None:
    pen = Pen("p", color=PALETTE[1], width=10, feather=0)
    window, controller, clock = make(pens=(pen,))
    click_toggle(window)
    controller.pointer_down(20, 100, 0.0)
    controller.pointer_move(280, 100, 0.1)
    controller.pointer_up(0.2)
    clock.now = 1.0  # after the points, as it always is in real use
    px = window.grab().toImage().pixelColor(150, 100)
    assert px.alpha() == 255
    assert px.red() > 240 and px.green() < 60  # still the pen's red
    window.close()


# -- reading modifier keys on each platform ------------------------------------

CTRL = Qt.KeyboardModifier.ControlModifier  # Control on Windows, Command on a Mac
META = Qt.KeyboardModifier.MetaModifier  # the Windows key; Control on a Mac
SHIFT = Qt.KeyboardModifier.ShiftModifier
ALT = Qt.KeyboardModifier.AltModifier


def keypress(key: Qt.Key, mods: Qt.KeyboardModifier) -> QKeyEvent:
    return QKeyEvent(QKeyEvent.Type.KeyPress, key, mods)


@pytest.mark.parametrize("platform", ["win32", "linux"])
def test_on_windows_and_linux_control_is_ctrl(
    platform: str, qapp: QApplication
) -> None:
    assert key_string(keypress(Qt.Key.Key_D, CTRL | SHIFT), platform) == "Ctrl+Shift+D"
    assert key_string(keypress(Qt.Key.Key_C, CTRL | ALT), platform) == "Ctrl+Alt+C"


@pytest.mark.parametrize("platform", ["win32", "linux"])
def test_the_windows_key_is_ignored_on_windows_and_linux(
    platform: str, qapp: QApplication
) -> None:
    assert key_string(keypress(Qt.Key.Key_D, META | SHIFT), platform) == "Shift+D"


def test_on_a_mac_the_control_key_is_ctrl(qapp: QApplication) -> None:
    """Qt reports a Mac's Control key as its Meta modifier."""
    assert key_string(keypress(Qt.Key.Key_D, META | SHIFT), "darwin") == "Ctrl+Shift+D"
    assert key_string(keypress(Qt.Key.Key_C, META | ALT), "darwin") == "Ctrl+Alt+C"
    assert key_string(keypress(Qt.Key.Key_X, META | SHIFT), "darwin") == "Ctrl+Shift+X"


def test_on_a_mac_the_command_key_is_cmd_and_never_ctrl(qapp: QApplication) -> None:
    """Qt reports Command as its Control modifier. It must not pass for Ctrl."""
    assert key_string(keypress(Qt.Key.Key_D, CTRL | SHIFT), "darwin") == "Cmd+Shift+D"
    assert key_string(keypress(Qt.Key.Key_D, CTRL), "darwin") == "Cmd+D"


def test_on_a_mac_holding_both_keys_is_both(qapp: QApplication) -> None:
    got = key_string(keypress(Qt.Key.Key_D, CTRL | META | SHIFT), "darwin")
    assert got == "Cmd+Ctrl+Shift+D"


def test_keys_without_modifiers_read_the_same_on_every_platform(
    qapp: QApplication,
) -> None:
    for platform in ("win32", "linux", "darwin"):
        none = Qt.KeyboardModifier.NoModifier
        assert key_string(keypress(Qt.Key.Key_3, none), platform) == "3"
        assert key_string(keypress(Qt.Key.Key_Escape, none), platform) == "Esc"
        assert key_string(keypress(Qt.Key.Key_BracketRight, none), platform) == "]"


def test_a_mac_users_control_shift_d_toggles_draw_mode(qapp: QApplication) -> None:
    window, controller, _ = make()
    window.platform = "darwin"
    window.keyPressEvent(keypress(Qt.Key.Key_D, META | SHIFT))  # Control+Shift+D
    assert controller.draw_mode
    window.close()


def test_a_mac_users_command_shift_d_does_not_toggle_draw_mode(
    qapp: QApplication,
) -> None:
    window, controller, _ = make()
    window.platform = "darwin"
    window.keyPressEvent(keypress(Qt.Key.Key_D, CTRL | SHIFT))  # Command+Shift+D
    assert not controller.draw_mode  # left alone for the Mac and other apps
    window.close()


def test_the_overlay_reads_keys_for_the_platform_it_runs_on(qapp: QApplication) -> None:
    import sys

    window, _, _ = make()
    assert window.platform == sys.platform
    window.close()
