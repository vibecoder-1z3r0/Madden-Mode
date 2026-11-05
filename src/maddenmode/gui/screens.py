"""The monitors Qt knows about, as plain data."""

from PySide6.QtCore import QRect
from PySide6.QtGui import QGuiApplication

from maddenmode.targeting import Rect, ScreenInfo


def list_screens() -> list[ScreenInfo]:
    """All screens. Qt lists the primary screen first."""
    screens = []
    for index, screen in enumerate(QGuiApplication.screens()):
        g = screen.geometry()
        screens.append(
            ScreenInfo(
                index=index,
                name=screen.name() or f"Screen {index + 1}",
                geometry=Rect(g.x(), g.y(), g.width(), g.height()),
                dpr=screen.devicePixelRatio(),
                primary=index == 0,
            )
        )
    return screens


def to_qrect(rect: Rect) -> QRect:
    return QRect(rect.x, rect.y, rect.width, rect.height)
