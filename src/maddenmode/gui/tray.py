"""System tray icon: shows the app is running and keeps Quit within reach."""

import time
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from maddenmode.controller import Controller
from maddenmode.palette import PALETTE


def make_icon(color: QColor, drawing: bool) -> QIcon:
    """A dot in the current pen color; ringed while draw mode is on."""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(14, 14, size - 28, size - 28)
    if drawing:
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 255, 255), 6))
        painter.drawEllipse(5, 5, size - 10, size - 10)
    painter.end()
    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    def __init__(
        self,
        controller: Controller,
        on_settings: Callable[[], object],
        on_quit: Callable[[], None],
        clock: Callable[[], float] = time.monotonic,
        on_target: Callable[[], object] | None = None,
    ) -> None:
        super().__init__()
        self.controller = controller
        self.clock = clock
        self.setToolTip("Madden Mode")

        menu = QMenu()
        self.menu = menu

        self.draw_action = menu.addAction("Draw mode")
        self.draw_action.setCheckable(True)
        self.draw_action.triggered.connect(lambda: controller.toggle_draw(self.clock()))

        menu.addSeparator()
        self.clear_action = menu.addAction("Clear all")
        self.clear_action.triggered.connect(controller.clear_all)
        self.fade_action = menu.addAction("Fade all")
        self.fade_action.triggered.connect(lambda: controller.fade_all(self.clock()))

        menu.addSeparator()
        self.pen_menu = menu.addMenu("Pen")
        self.pen_group = QActionGroup(menu)
        self.pen_actions: list[QAction] = []
        self.color_menu = menu.addMenu("Color")
        self.color_group = QActionGroup(menu)
        self.color_actions: list[QAction] = []
        for index, color in enumerate(PALETTE):
            action = self.color_menu.addAction(f"{index + 1}  {color.name}")
            action.setCheckable(True)
            self.color_group.addAction(action)
            action.triggered.connect(
                lambda _=False, i=index: controller.select_color(i)
            )
            self.color_actions.append(action)

        menu.addSeparator()
        self.toolbar_action = menu.addAction("Show toolbar")
        self.toolbar_action.setCheckable(True)
        self.toolbar_action.triggered.connect(controller.toggle_toolbar)
        self.target_action = menu.addAction("Where to draw...")
        self.target_action.triggered.connect(lambda: on_target() if on_target else None)
        self.settings_action = menu.addAction("Settings...")
        self.settings_action.triggered.connect(lambda: on_settings())
        menu.addSeparator()
        self.quit_action = menu.addAction("Quit")
        self.quit_action.triggered.connect(lambda: on_quit())

        self.setContextMenu(menu)
        controller.add_listener(self.refresh)
        self.refresh()

    def _rebuild_pen_actions(self) -> None:
        for action in self.pen_actions:
            self.pen_group.removeAction(action)
        self.pen_menu.clear()
        self.pen_actions = []
        for index, pen in enumerate(self.controller.pens):
            action = self.pen_menu.addAction(pen.name)
            action.setCheckable(True)
            self.pen_group.addAction(action)
            action.triggered.connect(
                lambda _=False, i=index: self.controller.select_pen(i)
            )
            self.pen_actions.append(action)

    def refresh(self) -> None:
        c = self.controller
        if [a.text() for a in self.pen_actions] != [p.name for p in c.pens]:
            self._rebuild_pen_actions()
        for index, action in enumerate(self.pen_actions):
            action.setChecked(index == c.pen_index)
        current = PALETTE.index(c.current_pen.color)
        for index, action in enumerate(self.color_actions):
            action.setChecked(index == current)
        self.draw_action.setChecked(c.draw_mode)
        self.toolbar_action.setChecked(c.toolbar_visible)
        r, g, b = c.current_pen.color.rgb
        self.setIcon(make_icon(QColor(r, g, b), c.draw_mode))
