"""System-wide hotkeys, so the draw/clear/fade keys work while a game has focus.

Qt has no global hotkeys, so each platform needs its own backend. Only the
Windows backend exists so far (RegisterHotKey).

!! WindowsHotkeys has NOT been run on Windows yet. It was written without
access to a Windows machine. The parts that need no Windows (parsing chords
into modifier and key codes, wiring bindings to the Controller) are tested;
the Win32 calls and the native event hook are not.
"""

import sys
from collections.abc import Callable
from typing import Any, Protocol

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication

from maddenmode.controller import Controller, global_bindings

# Win32 modifier flags for RegisterHotKey
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000  # holding the keys does not retrigger the action
WM_HOTKEY = 0x0312

_MODIFIERS = {"ctrl": MOD_CONTROL, "shift": MOD_SHIFT, "alt": MOD_ALT, "win": MOD_WIN}


class HotkeyBackend(Protocol):
    def register(self, bindings: dict[str, Callable[[], None]]) -> None:
        """Replace all registered hotkeys with `bindings` (chord -> callback)."""

    def unregister_all(self) -> None: ...


def parse_chord(chord: str) -> tuple[int, int]:
    """'Ctrl+Shift+D' -> (Win32 modifier flags, virtual-key code)."""
    *mods, key = [part.strip() for part in chord.split("+")]
    if not mods:
        raise ValueError(f"a global hotkey needs a modifier: {chord!r}")
    flags = MOD_NOREPEAT
    for mod in mods:
        try:
            flags |= _MODIFIERS[mod.lower()]
        except KeyError:
            raise ValueError(f"unknown modifier {mod!r} in {chord!r}") from None
    if len(key) == 1 and key.isalnum():
        vk = ord(key.upper())  # Win32 virtual keys for A-Z and 0-9 are their ASCII
    elif key.lower() == "esc":
        vk = 0x1B
    elif key.upper().startswith("F") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        vk = 0x70 + int(key[1:]) - 1
    else:
        raise ValueError(f"unsupported key {key!r} in {chord!r}")
    return flags, vk


def bind_controller(
    backend: HotkeyBackend, controller: Controller, clock: Callable[[], float]
) -> None:
    """Register the Controller's global keys (for its current prefix)."""

    def make_callback(chord: str) -> Callable[[], None]:
        def trigger() -> None:
            controller.press(chord, clock())

        return trigger

    backend.register(
        {
            chord: make_callback(chord)
            for chord in global_bindings(controller.settings.prefix)
        }
    )


class WindowsHotkeys(QAbstractNativeEventFilter):  # pragma: no cover
    """Global hotkeys through the Win32 RegisterHotKey API. UNVERIFIED."""

    def __init__(self) -> None:
        super().__init__()
        self._callbacks: dict[int, Callable[[], None]] = {}
        self._installed = False

    def register(self, bindings: dict[str, Callable[[], None]]) -> None:
        if sys.platform != "win32":
            raise OSError("WindowsHotkeys only works on Windows")
        import ctypes

        self.unregister_all()
        user32 = ctypes.windll.user32
        for hotkey_id, (chord, callback) in enumerate(bindings.items(), start=1):
            flags, vk = parse_chord(chord)
            if not user32.RegisterHotKey(None, hotkey_id, flags, vk):
                self.unregister_all()
                raise OSError(f"could not register {chord} (is another app using it?)")
            self._callbacks[hotkey_id] = callback
        if not self._installed:
            app = QCoreApplication.instance()
            if app is None:
                raise RuntimeError("create the QApplication before registering hotkeys")
            app.installNativeEventFilter(self)
            self._installed = True

    def unregister_all(self) -> None:
        if sys.platform == "win32":
            import ctypes

            for hotkey_id in self._callbacks:
                ctypes.windll.user32.UnregisterHotKey(None, hotkey_id)
        self._callbacks.clear()

    def nativeEventFilter(self, eventType: Any, message: Any) -> tuple[bool, int]:
        if sys.platform == "win32" and eventType == b"windows_generic_MSG":
            import ctypes
            import ctypes.wintypes

            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                callback = self._callbacks.get(msg.wParam)
                if callback is not None:
                    callback()
                    return True, 0
        return False, 0
