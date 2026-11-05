"""The small always-visible control panel.

It is its own window (not part of the click-through overlay) so it can be
clicked while the overlay lets mouse input pass through to the game. It never
takes keyboard focus, so clicking it does not pull focus away from the game
or the overlay.

It holds no state of its own: every widget is refreshed from the Controller,
so the toolbar, hotkeys and tray icon can never disagree.
"""

import time
from collections.abc import Callable

from PySide6.QtCore import QPoint, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QPushButton,
    QToolButton,
    QWidget,
)

from maddenmode.controller import Controller
from maddenmode.palette import PALETTE

SWATCH_SIZE = 24


class Toolbar(QWidget):
    def __init__(
        self,
        controller: Controller,
        on_settings: Callable[[], object],
        on_quit: Callable[[], None],
        clock: Callable[[], float] = time.monotonic,
        parent: QWidget | None = None,
        on_target: Callable[[], object] | None = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.clock = clock
        self._started = False
        self._drag_offset: QPoint | None = None

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setWindowTitle("Madden Mode")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        self.draw_button = self._button("Draw", "Toggle draw mode", checkable=True)
        self.draw_button.clicked.connect(lambda: controller.toggle_draw(self.clock()))
        # Draw mode takes over the mouse, so its state must be unmistakable.
        self.draw_button.setStyleSheet(
            "QPushButton:checked { background: #2e9e5b; color: white;"
            " font-weight: bold; }"
        )
        layout.addWidget(self.draw_button)

        self.swatches: list[QToolButton] = []
        for index, color in enumerate(PALETTE):
            swatch = QToolButton()
            swatch.setCheckable(True)
            swatch.setFixedSize(SWATCH_SIZE, SWATCH_SIZE)
            swatch.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            swatch.setToolTip(f"{color.name} (key {index + 1} while drawing)")
            swatch.setStyleSheet(
                f"QToolButton {{ background: {color.hex}; border: 2px solid #555;"
                f" border-radius: {SWATCH_SIZE // 2}px; }}"
                "QToolButton:checked { border: 3px solid #ffffff; }"
            )
            swatch.clicked.connect(lambda _=False, i=index: controller.select_color(i))
            self.swatches.append(swatch)
            layout.addWidget(swatch)

        self.pen_combo = QComboBox()
        self.pen_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pen_combo.setToolTip("Pen ( [ and ] while drawing )")
        self.pen_combo.currentIndexChanged.connect(self._on_pen_chosen)
        layout.addWidget(self.pen_combo)

        self.target_button = self._button("Target", "Choose a monitor or window")
        self.target_button.clicked.connect(lambda: on_target() if on_target else None)
        layout.addWidget(self.target_button)

        self.clear_button = self._button("Clear", "Clear everything now")
        self.clear_button.clicked.connect(controller.clear_all)
        layout.addWidget(self.clear_button)

        self.fade_button = self._button("Fade", "Fade everything out")
        self.fade_button.clicked.connect(lambda: controller.fade_all(self.clock()))
        layout.addWidget(self.fade_button)

        self.settings_button = self._button("Settings", "Open settings")
        self.settings_button.clicked.connect(lambda: on_settings())
        layout.addWidget(self.settings_button)

        self.quit_button = self._button("Quit", "Quit Madden Mode")
        self.quit_button.clicked.connect(lambda: on_quit())
        layout.addWidget(self.quit_button)

        controller.add_listener(self.refresh)
        self.refresh()

    @staticmethod
    def _button(text: str, tooltip: str, checkable: bool = False) -> QPushButton:
        button = QPushButton(text)
        button.setCheckable(checkable)
        button.setToolTip(tooltip)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return button

    # -- state ------------------------------------------------------------

    def start(self) -> None:
        """From now on, follow the controller's toolbar-visible flag."""
        self._started = True
        self.refresh()

    def refresh(self) -> None:
        c = self.controller
        self.draw_button.setChecked(c.draw_mode)

        current = PALETTE.index(c.current_pen.color)
        for index, swatch in enumerate(self.swatches):
            swatch.setChecked(index == current)

        names = [pen.name for pen in c.pens]
        shown = [self.pen_combo.itemText(i) for i in range(self.pen_combo.count())]
        self.pen_combo.blockSignals(True)
        if names != shown:
            self.pen_combo.clear()
            self.pen_combo.addItems(names)
        self.pen_combo.setCurrentIndex(c.pen_index)
        self.pen_combo.blockSignals(False)

        if self._started:
            was_visible = self.isVisible()
            self.setVisible(c.toolbar_visible)
            if c.toolbar_visible:
                # the overlay re-shows itself when draw mode changes; stay above it
                QTimer.singleShot(0, self.raise_)
            elif was_visible:
                self.hide()

    def _on_pen_chosen(self, index: int) -> None:
        if 0 <= index < len(self.controller.pens):
            self.controller.select_pen(index)

    # -- placement and dragging ------------------------------------------

    def move_to_top_right(self, screen: QRect, margin: int = 16) -> None:
        self.adjustSize()
        self.move(screen.right() - self.width() - margin, screen.top() + margin)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            self._drag_offset is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_offset = None

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(24, 24, 28, 235))
        painter.setPen(QColor(90, 90, 96))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 10, 10)
        painter.end()
