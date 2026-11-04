"""Try the overlay over a fake "game" window.  Run: python -m maddenmode.demo

A moving ball stands in for a game so you can see the overlay sit on top of
something that keeps animating. On Windows the global hotkeys are registered
so they work while the fake game has focus. Elsewhere, hotkeys only work
while the overlay itself has focus (i.e. in draw mode), so use --start-drawing.
"""

import argparse
import math
import sys
import time

from PySide6.QtCore import QPointF, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QApplication, QWidget

from maddenmode.controller import Controller, ModifierPrefix, Settings
from maddenmode.gui.hotkeys import WindowsHotkeys, bind_controller
from maddenmode.gui.overlay import OverlayWindow
from maddenmode.scene import Scene


class FakeGame(QWidget):  # pragma: no cover
    """Something that keeps moving, so click-through and frame rate are visible."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Fake game (Madden Mode demo)")
        self._t0 = time.monotonic()
        timer = QTimer(self)
        timer.timeout.connect(self.update)
        timer.start(16)
        self.clicks = 0

    def mousePressEvent(self, event: object) -> None:
        self.clicks += 1  # proves clicks reach the "game" when not drawing
        self.setWindowTitle(f"Fake game: {self.clicks} clicks reached me")

    def paintEvent(self, event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(34, 94, 52))
        t = time.monotonic() - self._t0
        x = self.width() / 2 + math.sin(t) * self.width() * 0.35
        y = self.height() / 2 + math.cos(t * 1.3) * self.height() * 0.3
        p.setBrush(QColor(240, 240, 240))
        p.drawEllipse(QPointF(x, y), 22, 22)
        p.end()


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--alt", action="store_true", help="use Ctrl+Alt instead of Ctrl+Shift"
    )
    parser.add_argument(
        "--hold", action="store_true", help="hold-to-draw instead of toggle"
    )
    parser.add_argument(
        "--start-drawing", action="store_true", help="begin in draw mode"
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    prefix = ModifierPrefix.CTRL_ALT if args.alt else ModifierPrefix.CTRL_SHIFT
    settings = Settings(prefix=prefix, hold_to_draw=args.hold)
    controller = Controller(Scene(), settings=settings)

    game = FakeGame()
    game.resize(900, 600)
    game.show()

    overlay = OverlayWindow(controller)
    overlay.setGeometry(game.geometry())
    overlay.start()

    if sys.platform == "win32":
        hotkeys = WindowsHotkeys()
        bind_controller(hotkeys, controller, time.monotonic)
    if args.start_drawing:
        controller.press(f"{prefix}+D", time.monotonic())

    print(f"{prefix}+D toggle draw | {prefix}+C clear all | {prefix}+F fade all")
    print("In draw mode: 1-8 color, [ ] pen, Esc exit")
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
