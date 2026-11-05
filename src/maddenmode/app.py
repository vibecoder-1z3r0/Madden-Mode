"""Wires the controller, overlay, toolbar, toast, tray and hotkeys together."""

import argparse
import sys
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Protocol

from PySide6.QtCore import QRect, QTimer
from PySide6.QtWidgets import QApplication, QDialog

from maddenmode import settings_store
from maddenmode.controller import Controller, Settings
from maddenmode.gui.follow import WindowFollower
from maddenmode.gui.hotkeys import HotkeyBackend, WindowsHotkeys, bind_controller
from maddenmode.gui.overlay import OverlayWindow
from maddenmode.gui.screens import list_screens, to_qrect
from maddenmode.gui.settings_dialog import SettingsDialog
from maddenmode.gui.target_dialog import TargetDialog
from maddenmode.gui.toast import Toast
from maddenmode.gui.toolbar import Toolbar
from maddenmode.gui.tray import TrayIcon
from maddenmode.pen import Pen
from maddenmode.scene import Scene
from maddenmode.targeting import (
    MonitorTarget,
    ScreenInfo,
    Target,
    WindowTarget,
    describe_target,
    resolve_monitor,
)
from maddenmode.windows import NullWindowBackend, WindowBackend, WindowKind


class SettingsPrompt(Protocol):
    def exec(self) -> int: ...

    def result_values(self) -> tuple[Settings, tuple[Pen, ...]]: ...


class TargetPrompt(Protocol):
    def exec(self) -> int: ...

    def result_target(self) -> Target | None: ...


def _default_dialog(settings: Settings, pens: tuple[Pen, ...]) -> SettingsPrompt:
    return SettingsDialog(settings, pens)


def _default_target_dialog(
    screens: list[ScreenInfo], backend: WindowBackend, current: Target
) -> TargetPrompt:
    return TargetDialog(screens, backend, current)


def _default_window_backend() -> WindowBackend:
    if sys.platform == "win32":
        from maddenmode.gui.windows_win32 import Win32WindowBackend

        return Win32WindowBackend()
    return NullWindowBackend()


class MaddenMode:
    def __init__(
        self,
        qapp: QApplication,
        settings_path: Path | None = None,
        clock: Callable[[], float] = time.monotonic,
        hotkeys: HotkeyBackend | None = None,
        dialog_factory: Callable[
            [Settings, tuple[Pen, ...]], SettingsPrompt
        ] = _default_dialog,
        window_backend: WindowBackend | None = None,
        screens: Callable[[], list[ScreenInfo]] = list_screens,
        target_dialog_factory: Callable[
            [list[ScreenInfo], WindowBackend, Target], TargetPrompt
        ] = _default_target_dialog,
    ) -> None:
        self.qapp = qapp
        self.clock = clock
        self.hotkeys = hotkeys
        self.dialog_factory = dialog_factory
        self.window_backend = (
            window_backend if window_backend is not None else _default_window_backend()
        )
        self.screens = screens
        self.target_dialog_factory = target_dialog_factory
        self.settings_path = settings_path or settings_store.default_path()

        settings, pens, self.load_warning = settings_store.load(self.settings_path)
        self.controller = Controller(Scene(), pens=pens, settings=settings)
        self.overlay = OverlayWindow(self.controller, clock=clock)
        self.toolbar = Toolbar(
            self.controller,
            self.open_settings,
            self.quit,
            clock=clock,
            on_target=self.open_target_dialog,
        )
        self.toast = Toast(self.controller)
        self.tray = TrayIcon(
            self.controller,
            self.open_settings,
            self.quit,
            clock,
            on_target=self.open_target_dialog,
        )
        self.follower = WindowFollower(
            self.overlay, self.window_backend, self.screens, self._window_gone
        )
        # Problems found while starting (bad settings file, hotkey clash).
        # They are also shown on screen; this list lets a smoke test fail on them.
        self.startup_errors: list[str] = []

    # -- lifecycle ----------------------------------------------------------

    def start(self, geometry: QRect | None = None) -> None:
        """Show everything. By default the overlay covers the chosen target;
        `geometry` overrides that with a fixed area (used by the demo and tests)."""
        if geometry is not None:
            self._show_area(geometry)
        else:
            self.apply_target()
        self.overlay.start()
        self.toolbar.start()
        self.tray.show()
        hotkey_error = self._bind_hotkeys()
        if self.load_warning:
            self.startup_errors.append(self.load_warning)
            self.toast.show_message(self.load_warning)
        if hotkey_error:
            self.startup_errors.append(hotkey_error)

    def quit(self) -> None:
        self.follower.stop()
        if self.hotkeys is not None:
            self.hotkeys.unregister_all()
        self.tray.hide()
        self.qapp.quit()

    # -- where to draw ------------------------------------------------------

    def _show_area(self, area: QRect) -> None:
        self.overlay.setGeometry(area)
        self.toolbar.move_to_top_right(area)

    def apply_target(self) -> None:
        """Size the overlay to the current target (a monitor or a pinned window)."""
        target = self.controller.target
        if isinstance(target, WindowTarget):
            if self.window_backend.get_state(target.handle).kind == WindowKind.GONE:
                self._fall_back_to_monitor(f"The window {target.title!r} is gone")
                return
            self.follower.follow(target)
            self.toolbar.move_to_top_right(self.overlay.geometry())
            return
        self.follower.stop()
        screens = self.screens()
        if not screens:
            self._show_area(QRect(0, 0, 1280, 720))
            return
        screen, fell_back = resolve_monitor(target.index, screens)
        self._show_area(to_qrect(screen.geometry))
        if fell_back:
            self.toast.show_message(
                f"Monitor {target.index + 1} was not found; using Monitor "
                f"{screen.index + 1}"
            )

    def set_target(self, target: Target) -> None:
        """Draw over `target`. A chosen monitor is remembered; a window is not."""
        self.controller.set_target(target)
        self.apply_target()
        if (
            isinstance(target, MonitorTarget)
            and self.controller.settings.monitor != target.index
        ):
            settings = replace(self.controller.settings, monitor=target.index)
            self.controller.apply_settings(settings, self.controller.pens)
            self._save_settings()
        self.toast.show_message(
            f"Drawing over: {describe_target(self.controller.target, self.screens())}"
        )

    def open_target_dialog(self) -> bool:
        """Show the picker. Returns True if a new target was chosen."""
        dialog = self.target_dialog_factory(
            self.screens(), self.window_backend, self.controller.target
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        target = dialog.result_target()
        if target is None:
            return False
        self.set_target(target)
        return True

    def _window_gone(self, target: WindowTarget) -> None:
        self._fall_back_to_monitor(f"The window {target.title!r} closed")

    def _fall_back_to_monitor(self, reason: str) -> None:
        monitor = MonitorTarget(self.controller.settings.monitor)
        self.controller.set_target(monitor)
        self.apply_target()
        self.toast.show_message(
            f"{reason}. Back to {describe_target(monitor, self.screens())}."
        )

    # -- settings -----------------------------------------------------------

    def open_settings(self) -> bool:
        """Show the settings dialog. Returns True if the user applied changes."""
        dialog = self.dialog_factory(self.controller.settings, self.controller.pens)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        settings, pens = dialog.result_values()
        self.apply(settings, pens)
        return True

    def apply(self, settings: Settings, pens: tuple[Pen, ...]) -> None:
        """Make new settings live, save them and re-register the hotkeys."""
        self.controller.apply_settings(settings, pens)
        self._save_settings()
        self._bind_hotkeys()

    def _save_settings(self) -> None:
        try:
            settings_store.save(
                self.settings_path, self.controller.settings, self.controller.pens
            )
        except OSError as err:
            self.toast.show_message(f"Could not save settings: {err.strerror or err}")

    def _bind_hotkeys(self) -> str | None:
        """Register the global hotkeys. Returns an error message, or None."""
        if self.hotkeys is None:
            return None
        try:
            bind_controller(self.hotkeys, self.controller, self.clock)
        except OSError as err:
            # e.g. another app already owns the chord: say so, don't crash
            self.toast.show_message(str(err))
            return str(err)
        return None


def run_smoke_test(app: MaddenMode, milliseconds: int = 500) -> int:
    """Start everything, let the event loop run briefly, then quit.

    Returns 0 if it started without problems and 1 otherwise. Used by CI to
    check that the real app starts on each platform, including registering
    the real global hotkeys on Windows.
    """
    app.start()

    def check_and_quit() -> None:
        # Check before quitting: quit() closes every window.
        if not app.overlay.isVisible():
            app.startup_errors.append("the overlay is not visible")
        if not app.toolbar.isVisible():
            app.startup_errors.append("the toolbar is not visible")
        app.quit()

    QTimer.singleShot(milliseconds, check_and_quit)
    app.qapp.exec()
    for error in app.startup_errors:
        print(f"startup problem: {error}", file=sys.stderr)
    return 1 if app.startup_errors else 0


def main(argv: list[str] | None = None) -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(
        prog="madden-mode", description="Telestration overlay"
    )
    parser.add_argument("--settings", type=Path, help="settings file to use")
    parser.add_argument(
        "--start-drawing", action="store_true", help="begin in draw mode"
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="start, run briefly and exit 0 if there were no problems (for CI)",
    )
    args = parser.parse_args(argv)

    qapp = QApplication(sys.argv[:1])
    qapp.setQuitOnLastWindowClosed(False)  # the tray icon keeps it alive
    hotkeys = WindowsHotkeys() if sys.platform == "win32" else None
    app = MaddenMode(qapp, settings_path=args.settings, hotkeys=hotkeys)
    if args.smoke_test:
        return run_smoke_test(app)
    app.start()
    if args.start_drawing:
        app.controller.set_draw_mode(True, time.monotonic())
    return qapp.exec()
