"""The app icon and the tray icon, drawn in code (no image files to ship).

Each size is drawn separately at that exact size, so the small tray sizes stay
crisp instead of being a shrunken big picture. The icon is a dark rounded tile
(so it shows on both light and dark taskbars) with a bright telestrator swoosh.
The tray version adds a dot in the current pen color, and a white ring while
draw mode is on.
"""

import sys

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QApplication

SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)
TILE = QColor(24, 24, 28)
SWOOSH = QColor(0, 229, 255)
RING = QColor(255, 255, 255)
APP_ID = "MaddenMode.Overlay"


def draw_icon(
    size: int, pen_color: QColor | None = None, drawing: bool = False
) -> QPixmap:
    """One icon image at exactly `size` pixels."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # the dark tile
    radius = size * 0.22
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(TILE)
    p.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

    # the swoosh: a stroke with a dot at its end, like a telestrator mark
    width = max(2.0, size * 0.11)
    path = QPainterPath(QPointF(size * 0.17, size * 0.66))
    path.cubicTo(
        QPointF(size * 0.35, size * 0.20),
        QPointF(size * 0.55, size * 0.80),
        QPointF(size * 0.82, size * 0.32),
    )
    pen = QPen(SWOOSH, width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(path)

    # the current pen color, as a dot in the lower right
    if pen_color is not None:
        dot = size * 0.21
        centre = QPointF(size * 0.72, size * 0.72)
        outline = QPen(TILE, max(1.0, size * 0.05))
        p.setPen(outline)
        p.setBrush(pen_color)
        p.drawEllipse(centre, dot, dot)

    # a white ring while drawing, so the state reads at a glance
    if drawing:
        ring_width = max(2.0, size * 0.09)
        inset = ring_width / 2 + size * 0.015
        p.setPen(QPen(RING, ring_width))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(
            QRectF(inset, inset, size - 2 * inset, size - 2 * inset),
            radius * 0.8,
            radius * 0.8,
        )

    p.end()
    return pixmap


def make_icon(pen_color: QColor | None = None, drawing: bool = False) -> QIcon:
    """An icon holding every size, each drawn at its own size."""
    icon = QIcon()
    for size in SIZES:
        icon.addPixmap(draw_icon(size, pen_color, drawing))
    return icon


def app_icon() -> QIcon:
    """The plain application icon (no pen-color dot)."""
    return make_icon()


def set_app_identity(app: QApplication) -> None:
    """Give the app its own name, icon and Windows taskbar identity.

    Without this, Windows groups the app under python.exe and shows Python's
    icon and name wherever it can. The tray list on Windows still names the
    program file until the app is packaged as its own executable.
    """
    app.setApplicationName("Madden Mode")
    app.setApplicationDisplayName("Madden Mode")
    app.setWindowIcon(app_icon())
    if sys.platform == "win32":
        import ctypes

        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except (AttributeError, OSError):
            pass  # cosmetic only: never stop the app over a taskbar label
