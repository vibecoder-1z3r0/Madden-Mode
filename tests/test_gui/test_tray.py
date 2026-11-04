from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from maddenmode.controller import Controller
from maddenmode.gui.tray import TrayIcon, make_icon
from maddenmode.palette import PALETTE
from maddenmode.pen import Pen
from maddenmode.scene import Scene


def make() -> tuple[TrayIcon, Controller, list[str]]:
    controller = Controller(Scene())
    calls: list[str] = []
    tray = TrayIcon(
        controller,
        lambda: calls.append("settings") or True,
        lambda: calls.append("quit"),
        clock=lambda: 3.0,
    )
    return tray, controller, calls


def test_menu_has_quit_and_settings(qapp: QApplication) -> None:
    tray, _, calls = make()
    tray.settings_action.trigger()
    tray.quit_action.trigger()
    assert calls == ["settings", "quit"]


def test_draw_action_toggles_draw_mode(qapp: QApplication) -> None:
    tray, controller, _ = make()
    tray.draw_action.trigger()
    assert controller.draw_mode
    assert tray.draw_action.isChecked()
    tray.draw_action.trigger()
    assert not controller.draw_mode


def test_clear_and_fade_actions(qapp: QApplication) -> None:
    tray, controller, _ = make()
    controller.scene.begin_stroke(Pen("p"), 0, 0, 0.0)
    tray.fade_action.trigger()
    assert controller.scene.strokes[0].cleared_at == 3.0
    tray.clear_action.trigger()
    assert controller.scene.strokes == []


def test_pen_submenu_lists_and_selects_pens(qapp: QApplication) -> None:
    tray, controller, _ = make()
    assert [a.text() for a in tray.pen_actions] == [p.name for p in controller.pens]
    tray.pen_actions[2].trigger()
    assert controller.pen_index == 2
    assert tray.pen_actions[2].isChecked()
    assert not tray.pen_actions[0].isChecked()


def test_color_submenu_selects_colors(qapp: QApplication) -> None:
    tray, controller, _ = make()
    assert len(tray.color_actions) == 8
    tray.color_actions[6].trigger()
    assert controller.current_pen.color == PALETTE[6]
    assert tray.color_actions[6].isChecked()


def test_toolbar_action_follows_and_drives_visibility(qapp: QApplication) -> None:
    tray, controller, _ = make()
    assert tray.toolbar_action.isChecked()
    tray.toolbar_action.trigger()
    assert not controller.toolbar_visible
    controller.toggle_toolbar()
    assert tray.toolbar_action.isChecked()


def test_pen_menu_is_rebuilt_when_pens_change(qapp: QApplication) -> None:
    tray, controller, _ = make()
    controller.apply_settings(controller.settings, (Pen("one"), Pen("two")))
    assert [a.text() for a in tray.pen_actions] == ["one", "two"]


def test_icon_shows_the_pen_color_and_a_ring_while_drawing(qapp: QApplication) -> None:
    red = QColor(255, 0, 0)
    idle = make_icon(red, drawing=False).pixmap(64, 64).toImage()
    active = make_icon(red, drawing=True).pixmap(64, 64).toImage()
    assert idle.pixelColor(32, 32).red() == 255
    assert idle.pixelColor(32, 32).green() == 0
    assert idle.pixelColor(7, 32).alpha() == 0  # no ring when idle
    assert active.pixelColor(7, 32).alpha() > 0  # ring when drawing


def test_icon_follows_the_controller(qapp: QApplication) -> None:
    tray, controller, _ = make()
    controller.select_color(1)  # red
    pixmap = tray.icon().pixmap(64, 64).toImage()
    assert pixmap.pixelColor(32, 32).red() > 200
    assert pixmap.pixelColor(32, 32).green() < 100
