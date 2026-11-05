"""Keeps the overlay on top of a pinned window as it moves, resizes or goes away.

Polling (every 100 ms) is the simple, dependable way to track another
application's window. Strokes are stored in the overlay's own coordinates, so
they move with the window; they are not rescaled if the window is resized.
"""

from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer

from maddenmode.gui.overlay import OverlayWindow
from maddenmode.gui.screens import to_qrect
from maddenmode.targeting import Rect, ScreenInfo, WindowTarget, physical_to_logical
from maddenmode.windows import WindowBackend, WindowKind

POLL_MS = 100


class WindowFollower(QObject):
    def __init__(
        self,
        overlay: OverlayWindow,
        backend: WindowBackend,
        screens: Callable[[], list[ScreenInfo]],
        on_gone: Callable[[WindowTarget], None],
        interval_ms: int = POLL_MS,
    ) -> None:
        super().__init__(overlay)
        self.overlay = overlay
        self.backend = backend
        self.screens = screens
        self.on_gone = on_gone
        self.target: WindowTarget | None = None
        self._hidden = False  # hidden by us because the window is not showing
        self._last: Rect | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.tick)

    @property
    def active(self) -> bool:
        return self.target is not None

    def follow(self, target: WindowTarget) -> None:
        self.target = target
        self._hidden = False
        self._last = None
        self._timer.start()
        self.tick()

    def stop(self) -> None:
        self._timer.stop()
        self.target = None
        self._last = None
        if self._hidden:
            self._hidden = False
            self.overlay.show()

    def tick(self) -> None:
        target = self.target
        if target is None:
            return
        state = self.backend.get_state(target.handle)
        if state.kind == WindowKind.GONE:
            self.stop()
            self.on_gone(target)
            return
        if state.kind == WindowKind.MINIMIZED or state.rect is None:
            if self.overlay.isVisible():
                # never leave a stroke half-drawn on a window we cannot see
                self.overlay.controller.pointer_up(self.overlay.clock())
                self.overlay.hide()
                self._hidden = True
            return
        if self._hidden:
            self._hidden = False
            self.overlay.show()
        logical = physical_to_logical(state.rect, self.screens())
        if logical != self._last:
            self._last = logical
            self.overlay.setGeometry(to_qrect(logical))
