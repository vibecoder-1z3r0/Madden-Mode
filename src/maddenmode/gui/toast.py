"""A brief on-screen message when the pen, color or draw mode changes.

Click-through and never takes focus, so it cannot get in the way. It shows for
about a second and fades out, like the strokes do.
"""

from PySide6.QtCore import QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QPainter,
    QPaintEvent,
)
from PySide6.QtWidgets import QWidget

from maddenmode.controller import Controller
from maddenmode.labels import describe_pen

SHOW_MS = 1200
FADE_MS = 300
PAD_X, PAD_Y = 16, 9


class Toast(QWidget):
    def __init__(self, controller: Controller, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.text = ""

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )

        self._font = QFont()
        self._font.setPointSize(12)
        self._font.setBold(True)

        self._hold = QTimer(self)
        self._hold.setSingleShot(True)
        self._hold.setInterval(SHOW_MS)
        self._hold.timeout.connect(self._start_fade)

        self._fade = QPropertyAnimation(self, b"windowOpacity")
        self._fade.setDuration(FADE_MS)
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.finished.connect(self._hide_now)

        self._last = self._snapshot()
        controller.add_listener(self._on_change)

    # -- what changed -------------------------------------------------------

    def _snapshot(self) -> tuple[bool, str, str]:
        pen = self.controller.current_pen
        return self.controller.draw_mode, pen.name, pen.color.name

    def _on_change(self) -> None:
        draw_mode, pen_name, color_name = self._snapshot()
        was_drawing, was_pen, was_color = self._last
        self._last = (draw_mode, pen_name, color_name)
        if draw_mode != was_drawing:
            self.show_message(f"Draw mode {'ON' if draw_mode else 'OFF'}")
        elif (pen_name, color_name) != (was_pen, was_color):
            self.show_message(describe_pen(self.controller.current_pen))

    # -- showing ------------------------------------------------------------

    def show_message(self, text: str) -> None:
        self.text = text
        metrics = QFontMetrics(self._font)
        self.setFixedSize(
            metrics.horizontalAdvance(text) + 2 * PAD_X, metrics.height() + 2 * PAD_Y
        )
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            area = screen.geometry()
            self.move(area.center().x() - self.width() // 2, area.top() + 48)
        self._fade.stop()
        self.setWindowOpacity(1.0)
        self.show()
        self.update()
        self._hold.start()

    def _start_fade(self) -> None:
        self._fade.start()

    def _hide_now(self) -> None:
        self._hold.stop()
        self._fade.stop()
        self.hide()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(20, 20, 24, 225))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 12, 12)
        painter.setFont(self._font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text)
        painter.end()
