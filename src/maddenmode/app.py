"""Wires the controller, overlay, toolbar, toast, tray and hotkeys together."""

import argparse
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from PySide6.QtCore import QRect
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QDialog

from maddenmode import settings_store
from maddenmode.controller import Controller, Settings
from maddenmode.gui.hotkeys import HotkeyBackend, WindowsHotkeys, bind_controller
from maddenmode.gui.overlay import OverlayWindow
from maddenmode.gui.settings_dialog import SettingsDialog
from maddenmode.gui.toast import Toast
from maddenmode.gui.toolbar import Toolbar
from maddenmode.gui.tray import TrayIcon
from maddenmode.pen import Pen
from maddenmode.scene import Scene


class SettingsPrompt(Protocol):
    def exec(self) -> int: ...

    def result_values(self) -> tuple[Settings, tuple[Pen, ...]]: ...


def _default_dialog(settings: Settings, pens: tuple[Pen, ...]) -> SettingsPrompt:
    return SettingsDialog(settings, pens)


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
    ) -> None:
        self.qapp = qapp
        self.clock = clock
        self.hotkeys = hotkeys
        self.dialog_factory = dialog_factory
        self.settings_path = settings_path or settings_store.default_path()

        settings, pens, self.load_warning = settings_store.load(self.settings_path)
        self.controller = Controller(Scene(), pens=pens, settings=settings)
        self.overlay = OverlayWindow(self.controller, clock=clock)
        self.toolbar = Toolbar(
            self.controller, self.open_settings, self.quit, clock=clock
        )
        self.toast = Toast(self.controller)
        self.tray = TrayIcon(self.controller, self.open_settings, self.quit, clock)

    # -- lifecycle ----------------------------------------------------------

    def start(self, geometry: QRect | None = None) -> None:
        """Show everything. `geometry` defaults to the primary screen."""
        if geometry is None:
            screen = QGuiApplication.primaryScreen()
            geometry = (
                screen.geometry() if screen is not None else QRect(0, 0, 1280, 720)
            )
        self.overlay.setGeometry(geometry)
        self.overlay.start()
        self.toolbar.move_to_top_right(geometry)
        self.toolbar.start()
        self.tray.show()
        self._bind_hotkeys()
        if self.load_warning:
            self.toast.show_message(self.load_warning)

    def quit(self) -> None:
        if self.hotkeys is not None:
            self.hotkeys.unregister_all()
        self.tray.hide()
        self.qapp.quit()

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
        try:
            settings_store.save(self.settings_path, settings, pens)
        except OSError as err:
            self.toast.show_message(f"Could not save settings: {err.strerror or err}")
        self._bind_hotkeys()

    def _bind_hotkeys(self) -> None:
        if self.hotkeys is None:
            return
        try:
            bind_controller(self.hotkeys, self.controller, self.clock)
        except OSError as err:
            # e.g. another app already owns the chord: say so, don't crash
            self.toast.show_message(str(err))


def main(argv: list[str] | None = None) -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(
        prog="madden-mode", description="Telestration overlay"
    )
    parser.add_argument("--settings", type=Path, help="settings file to use")
    parser.add_argument(
        "--start-drawing", action="store_true", help="begin in draw mode"
    )
    args = parser.parse_args(argv)

    qapp = QApplication(sys.argv[:1])
    qapp.setQuitOnLastWindowClosed(False)  # the tray icon keeps it alive
    hotkeys = WindowsHotkeys() if sys.platform == "win32" else None
    app = MaddenMode(qapp, settings_path=args.settings, hotkeys=hotkeys)
    app.start()
    if args.start_drawing:
        app.controller.set_draw_mode(True, time.monotonic())
    return qapp.exec()
