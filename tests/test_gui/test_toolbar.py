from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from maddenmode.controller import Controller
from maddenmode.gui.toolbar import Toolbar
from maddenmode.palette import PALETTE
from maddenmode.pen import Pen
from maddenmode.scene import Scene


class Calls:
    def __init__(self) -> None:
        self.settings = 0
        self.quit = 0

    def on_settings(self) -> bool:
        self.settings += 1
        return True

    def on_quit(self) -> None:
        self.quit += 1


def make() -> tuple[Toolbar, Controller, Calls]:
    controller = Controller(Scene())
    calls = Calls()
    toolbar = Toolbar(controller, calls.on_settings, calls.on_quit, clock=lambda: 7.0)
    return toolbar, controller, calls


def mouse(
    kind: QEvent.Type, global_pos: QPoint, buttons: Qt.MouseButton
) -> QMouseEvent:
    return QMouseEvent(
        kind,
        QPointF(5, 5),
        QPointF(global_pos),
        Qt.MouseButton.LeftButton,
        buttons,
        Qt.KeyboardModifier.NoModifier,
    )


def test_has_a_swatch_per_palette_color_and_a_pen_choice(qapp: QApplication) -> None:
    toolbar, controller, _ = make()
    assert len(toolbar.swatches) == len(PALETTE) == 8
    assert [
        toolbar.pen_combo.itemText(i) for i in range(toolbar.pen_combo.count())
    ] == [p.name for p in controller.pens]


def test_never_takes_keyboard_focus(qapp: QApplication) -> None:
    toolbar, _, _ = make()
    assert toolbar.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus
    assert toolbar.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    for button in (toolbar.draw_button, toolbar.clear_button, toolbar.quit_button):
        assert button.focusPolicy() == Qt.FocusPolicy.NoFocus


def test_clicking_a_swatch_picks_that_color(qapp: QApplication) -> None:
    toolbar, controller, _ = make()
    toolbar.swatches[4].click()
    assert controller.current_pen.color == PALETTE[4]
    assert toolbar.swatches[4].isChecked()
    assert sum(s.isChecked() for s in toolbar.swatches) == 1


def test_draw_button_toggles_draw_mode_both_ways(qapp: QApplication) -> None:
    toolbar, controller, _ = make()
    toolbar.draw_button.click()
    assert controller.draw_mode
    assert toolbar.draw_button.isChecked()
    toolbar.draw_button.click()
    assert not controller.draw_mode
    assert not toolbar.draw_button.isChecked()


def test_pen_combo_selects_the_pen(qapp: QApplication) -> None:
    toolbar, controller, _ = make()
    toolbar.pen_combo.setCurrentIndex(2)
    assert controller.pen_index == 2


def test_clear_and_fade_buttons(qapp: QApplication) -> None:
    toolbar, controller, _ = make()
    controller.scene.begin_stroke(Pen("p"), 0, 0, 0.0)
    toolbar.fade_button.click()
    assert controller.scene.strokes[0].cleared_at == 7.0  # the injected clock
    toolbar.clear_button.click()
    assert controller.scene.strokes == []


def test_settings_and_quit_buttons_call_back(qapp: QApplication) -> None:
    toolbar, _, calls = make()
    toolbar.settings_button.click()
    toolbar.quit_button.click()
    assert (calls.settings, calls.quit) == (1, 1)


def test_follows_changes_made_elsewhere(qapp: QApplication) -> None:
    toolbar, controller, _ = make()
    controller.press("Ctrl+Shift+D", 0.0)
    assert toolbar.draw_button.isChecked()
    controller.press("3", 0.0)
    assert toolbar.swatches[2].isChecked()
    controller.press("]", 0.0)
    assert toolbar.pen_combo.currentIndex() == 1
    controller.press("Esc", 0.0)
    assert not toolbar.draw_button.isChecked()


def test_visibility_follows_the_controller_after_start(qapp: QApplication) -> None:
    toolbar, controller, _ = make()
    assert not toolbar.isVisible()  # nothing shows before start()
    toolbar.start()
    assert toolbar.isVisible()
    controller.toggle_toolbar()
    assert not toolbar.isVisible()
    controller.toggle_toolbar()
    assert toolbar.isVisible()
    toolbar.close()


def test_new_pens_repopulate_the_combo(qapp: QApplication) -> None:
    toolbar, controller, _ = make()
    controller.apply_settings(controller.settings, (Pen("solo"), Pen("duo")))
    assert [
        toolbar.pen_combo.itemText(i) for i in range(toolbar.pen_combo.count())
    ] == [
        "solo",
        "duo",
    ]


def test_can_be_dragged(qapp: QApplication) -> None:
    toolbar, _, _ = make()
    toolbar.move(50, 50)
    toolbar.mousePressEvent(
        mouse(QEvent.Type.MouseButtonPress, QPoint(100, 100), Qt.MouseButton.LeftButton)
    )
    toolbar.mouseMoveEvent(
        mouse(QEvent.Type.MouseMove, QPoint(200, 160), Qt.MouseButton.LeftButton)
    )
    assert toolbar.pos() == QPoint(150, 110)
    toolbar.mouseReleaseEvent(
        mouse(QEvent.Type.MouseButtonRelease, QPoint(200, 160), Qt.MouseButton.NoButton)
    )
    toolbar.mouseMoveEvent(
        mouse(QEvent.Type.MouseMove, QPoint(400, 400), Qt.MouseButton.LeftButton)
    )
    assert toolbar.pos() == QPoint(150, 110)  # released: no longer follows


def test_moves_to_the_top_right_of_a_screen(qapp: QApplication) -> None:
    toolbar, _, _ = make()
    toolbar.move_to_top_right(QRect(0, 0, 1000, 600), margin=16)
    assert toolbar.pos().x() == 999 - toolbar.width() - 16
    assert toolbar.pos().y() == 16


def test_paints_a_rounded_background(qapp: QApplication) -> None:
    toolbar, _, _ = make()
    toolbar.resize(toolbar.sizeHint())
    image = toolbar.grab().toImage()
    # inside the left margin the dark panel is drawn nearly opaque...
    assert image.pixelColor(5, image.height() // 2).alpha() > 200
    # ...and the rounded corner leaves the very corner transparent
    assert image.pixelColor(0, 0).alpha() == 0


def test_draw_button_is_clearly_colored_only_while_drawing(qapp: QApplication) -> None:
    toolbar, controller, _ = make()
    toolbar.show()

    def edge_pixel() -> tuple[int, int, int]:
        image = toolbar.draw_button.grab().toImage()
        c = image.pixelColor(4, image.height() // 2)
        return c.red(), c.green(), c.blue()

    r, g, b = edge_pixel()
    assert not (g > r + 40 and g > b + 40)  # idle: neutral
    controller.toggle_draw(0.0)
    r, g, b = edge_pixel()
    assert g > r + 40 and g > b + 40  # drawing: green
    toolbar.close()


def test_target_button_calls_back(qapp: QApplication) -> None:
    hits: list[int] = []
    controller = Controller(Scene())
    toolbar = Toolbar(
        controller, lambda: True, lambda: None, on_target=lambda: hits.append(1)
    )
    toolbar.target_button.click()
    assert hits == [1]


def test_target_button_without_a_callback_is_harmless(qapp: QApplication) -> None:
    toolbar, _, _ = make()
    toolbar.target_button.click()  # no callback was given: must not raise
