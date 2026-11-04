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
