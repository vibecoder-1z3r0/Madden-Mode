from PySide6.QtWidgets import QApplication

from maddenmode.controller import Controller
from maddenmode.gui.follow import WindowFollower
from maddenmode.gui.overlay import OverlayWindow
from maddenmode.scene import Scene
from maddenmode.targeting import Rect, ScreenInfo, WindowTarget
from maddenmode.windows import WindowInfo, WindowKind, WindowState

SCREEN = ScreenInfo(0, "Main", Rect(0, 0, 1920, 1080), 1.0, primary=True)
SCALED = ScreenInfo(0, "Scaled", Rect(0, 0, 1280, 720), 1.5, primary=True)
TARGET = WindowTarget(99, "Game")


class FakeBackend:
    available = True

    def __init__(self) -> None:
        self.state = WindowState(WindowKind.VISIBLE, Rect(100, 50, 800, 600))
        self.asked: list[int] = []

    def list_windows(self) -> list[WindowInfo]:
        return []

    def get_state(self, handle: int) -> WindowState:
        self.asked.append(handle)
        return self.state


def make(
    screens: list[ScreenInfo] | None = None,
) -> tuple[WindowFollower, OverlayWindow, FakeBackend, list[WindowTarget]]:
    backend = FakeBackend()
    gone: list[WindowTarget] = []
    controller = Controller(Scene())
    overlay = OverlayWindow(controller, clock=lambda: 5.0)
    overlay.show()
    follower = WindowFollower(
        overlay, backend, lambda: screens or [SCREEN], gone.append, interval_ms=1000
    )
    return follower, overlay, backend, gone


def geometry(overlay: OverlayWindow) -> tuple[int, int, int, int]:
    g = overlay.geometry()
    return g.x(), g.y(), g.width(), g.height()


def test_following_sizes_the_overlay_to_the_window(qapp: QApplication) -> None:
    follower, overlay, backend, _ = make()
    follower.follow(TARGET)
    assert follower.active
    assert geometry(overlay) == (100, 50, 800, 600)
    assert backend.asked == [99]
    follower.stop()
    overlay.close()


def test_the_overlay_follows_a_moving_and_resizing_window(qapp: QApplication) -> None:
    follower, overlay, backend, _ = make()
    follower.follow(TARGET)
    backend.state = WindowState(WindowKind.VISIBLE, Rect(300, 200, 640, 480))
    follower.tick()
    assert geometry(overlay) == (300, 200, 640, 480)
    follower.stop()
    overlay.close()


def test_physical_pixels_are_converted_for_a_scaled_screen(qapp: QApplication) -> None:
    follower, overlay, backend, _ = make(screens=[SCALED])
    backend.state = WindowState(WindowKind.VISIBLE, Rect(300, 150, 900, 600))
    follower.follow(TARGET)
    assert geometry(overlay) == (200, 100, 600, 400)  # divided by 1.5
    follower.stop()
    overlay.close()


def test_geometry_is_only_set_when_the_window_changes(qapp: QApplication) -> None:
    follower, overlay, _, _ = make()
    follower.follow(TARGET)
    overlay.setGeometry(0, 0, 10, 10)  # someone else changes it
    follower.tick()  # window unchanged: we must not fight for it every tick
    assert geometry(overlay) == (0, 0, 10, 10)
    follower.stop()
    overlay.close()


def test_a_minimized_window_hides_the_overlay_and_ends_the_stroke(
    qapp: QApplication,
) -> None:
    follower, overlay, backend, _ = make()
    controller = overlay.controller
    controller.set_draw_mode(True, 5.0)
    controller.pointer_down(1, 1, 5.0)
    follower.follow(TARGET)
    backend.state = WindowState(WindowKind.MINIMIZED)
    follower.tick()
    assert not overlay.isVisible()
    assert controller.active_stroke is None  # no half-drawn stroke left behind
    follower.stop()
    overlay.close()


def test_the_overlay_returns_when_the_window_does(qapp: QApplication) -> None:
    follower, overlay, backend, _ = make()
    follower.follow(TARGET)
    backend.state = WindowState(WindowKind.MINIMIZED)
    follower.tick()
    backend.state = WindowState(WindowKind.VISIBLE, Rect(10, 10, 700, 500))
    follower.tick()
    assert overlay.isVisible()
    assert geometry(overlay) == (10, 10, 700, 500)
    follower.stop()
    overlay.close()


def test_a_closed_window_stops_following_and_reports_it(qapp: QApplication) -> None:
    follower, overlay, backend, gone = make()
    follower.follow(TARGET)
    backend.state = WindowState(WindowKind.GONE)
    follower.tick()
    assert gone == [TARGET]
    assert not follower.active
    follower.tick()  # no target any more: harmless
    assert gone == [TARGET]
    overlay.close()


def test_stopping_while_hidden_shows_the_overlay_again(qapp: QApplication) -> None:
    follower, overlay, backend, _ = make()
    follower.follow(TARGET)
    backend.state = WindowState(WindowKind.MINIMIZED)
    follower.tick()
    follower.stop()
    assert overlay.isVisible()
    overlay.close()


def test_a_visible_window_without_a_rect_is_treated_as_not_showing(
    qapp: QApplication,
) -> None:
    follower, overlay, backend, _ = make()
    follower.follow(TARGET)
    backend.state = WindowState(WindowKind.VISIBLE, None)
    follower.tick()
    assert not overlay.isVisible()
    follower.stop()
    overlay.close()
