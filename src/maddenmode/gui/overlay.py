"""The overlay window: transparent, always on top, click-through until drawing.

All decisions live in the Controller; this class only translates Qt events
into controller calls and paints the scene. How the window switches between
click-through and catching clicks is in `clickthrough` (a Qt flag everywhere
except Windows, where the window style is set directly).

Set MADDEN_DEBUG=1 to print the window's state each time draw mode changes.
"""

import os
import sys
import time
from collections.abc import Callable

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QShowEvent,
)
from PySide6.QtWidgets import QWidget

from maddenmode.controller import Controller
from maddenmode.gui import clickthrough
from maddenmode.gui.keys import key_string
from maddenmode.gui.render import paint_scene

FRAME_INTERVAL_MS = 16  # about 60 frames per second
BORDER_PX = 4  # the draw-mode indicator


def _hit_alpha() -> int:
    """MADDEN_HIT_ALPHA overrides the default: a troubleshooting escape hatch."""
    try:
        return max(1, min(255, int(os.environ.get("MADDEN_HIT_ALPHA", "2"))))
    except ValueError:
        return 2


# While drawing, the whole overlay is filled with this almost-invisible alpha
# (out of 255). On Windows a translucent window is hit-tested per pixel, and
# pixels with alpha 0 let mouse clicks fall through to the window underneath,
# whatever the click-through setting says. Any non-zero alpha makes the pixel
# catch the click. 2/255 is below what the eye can see.
HIT_ALPHA = _hit_alpha()


def debug_enabled() -> bool:
    return bool(os.environ.get("MADDEN_DEBUG"))


class OverlayWindow(QWidget):
    def __init__(
        self,
        controller: Controller,
        clock: Callable[[], float] = time.monotonic,
        parent: QWidget | None = None,
        click_through: clickthrough.ClickThrough | None = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.clock = clock
        self.controller.on_draw_mode_changed = self._apply_mode
        self.click_through = click_through or clickthrough.default_click_through(
            QGuiApplication.platformName()
        )
        self._catching_clicks = False  # click-through until draw mode starts

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        # starts click-through; the window is not shown yet, so this just sets
        # the flag (or, on Windows, is applied when the window first shows)
        if not self.click_through.reapply_on_show:
            self.click_through.apply(self, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._timer = QTimer(self)
        self._timer.setInterval(FRAME_INTERVAL_MS)
        self._timer.timeout.connect(self.tick)

    # -- lifecycle --------------------------------------------------------

    def start(self) -> None:
        """Show the overlay and start animating."""
        self.show()
        self._timer.start()

    def tick(self) -> None:
        """One animation frame: drop faded strokes and repaint."""
        self.controller.scene.prune(self.clock())
        self.update()

    # -- mode -------------------------------------------------------------

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if self.click_through.reapply_on_show:
            # Windows may reset the style when the window is (re)shown
            self.click_through.apply(self, not self._catching_clicks)

    def _apply_mode(self, drawing: bool) -> None:
        self._catching_clicks = drawing
        self.click_through.apply(self, not drawing)
        if drawing:
            self.setCursor(Qt.CursorShape.CrossCursor)
            self.activateWindow()
            self.raise_()
            self.setFocus()
        else:
            self.unsetCursor()
        self.update()
        if debug_enabled():
            self._print_debug(drawing)

    def _print_debug(self, drawing: bool) -> None:
        parts = [
            f"draw_mode={drawing}",
            f"qt_platform={QGuiApplication.platformName()}",
            f"switch={type(self.click_through).__name__}",
            f"visible={self.isVisible()}",
            f"geometry={self.geometry().getRect()}",
            f"hit_alpha={HIT_ALPHA}",
        ]
        if sys.platform == "win32" and self.click_through.reapply_on_show:
            exstyle = clickthrough.get_exstyle(int(self.winId()))
            parts.append(f"exstyle=0x{exstyle:08x}")
            parts.append(f"click_through={clickthrough.is_click_through(exstyle)}")
        print("[madden]", " ".join(parts), file=sys.stderr, flush=True)

    # -- painting ---------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.controller.draw_mode:
            painter.fillRect(self.rect(), QColor(0, 0, 0, HIT_ALPHA))
        paint_scene(painter, self.controller.scene, self.clock())
        if self.controller.draw_mode:
            self._paint_indicator(painter)
        painter.end()

    def _paint_indicator(self, painter: QPainter) -> None:
        """A thin border in the current pen color: draw mode is always visible."""
        r, g, b = self.controller.current_pen.color.rgb
        painter.setOpacity(1.0)
        painter.setPen(QPen(QColor(r, g, b), BORDER_PX))
        half = BORDER_PX // 2
        painter.drawRect(
            QRect(half, half, self.width() - BORDER_PX, self.height() - BORDER_PX)
        )

    # -- input ------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            self.controller.pointer_down(pos.x(), pos.y(), self.clock())
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        self.controller.pointer_move(pos.x(), pos.y(), self.clock())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.controller.pointer_up(self.clock())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = key_string(event)
        if key is not None and not event.isAutoRepeat():
            if self.controller.press(key, self.clock()):
                self.update()
                event.accept()
                return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        key = key_string(event)
        if key is not None and not event.isAutoRepeat():
            if self.controller.release(key, self.clock()):
                self.update()
                event.accept()
                return
        super().keyReleaseEvent(event)
