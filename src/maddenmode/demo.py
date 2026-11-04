"""Try Madden Mode over a fake "game" window.  Run: python -m maddenmode.demo

A moving ball stands in for a game so you can see the overlay sit on top of
something that keeps animating, and see clicks reach it when you are not
drawing. Settings go to a temporary file so your real settings are untouched.
"""

import math
import sys
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QPointF, QTimer
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import QApplication, QWidget

from maddenmode.app import MaddenMode
from maddenmode.gui.hotkeys import WindowsHotkeys


class FakeGame(QWidget):  # pragma: no cover
    """Something that keeps moving, so click-through and frame rate are visible."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Fake game (Madden Mode demo)")
        self._t0 = time.monotonic()
        self.clicks = 0
        timer = QTimer(self)
        timer.timeout.connect(self.update)
        timer.start(16)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.clicks += 1  # proves clicks reach the "game" when not drawing
        self.setWindowTitle(f"Fake game: {self.clicks} clicks reached me")

    def paintEvent(self, event: QPaintEvent) -> None:
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
    qapp = QApplication(sys.argv[:1])
    qapp.setQuitOnLastWindowClosed(False)

    game = FakeGame()
    game.resize(1000, 650)
    game.show()

    settings = Path(tempfile.mkdtemp(prefix="madden-mode-demo-")) / "settings.json"
    hotkeys = WindowsHotkeys() if sys.platform == "win32" else None
    app = MaddenMode(qapp, settings_path=settings, hotkeys=hotkeys)
    app.start(geometry=game.geometry())
    print("Ctrl+Shift+D draw | C clear all | F fade all | H show/hide toolbar")
    print("While drawing: 1-8 color, [ ] pen, Esc exit. Quit from the toolbar or tray.")
    return qapp.exec()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
