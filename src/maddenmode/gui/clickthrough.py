"""Switching the overlay between click-through and catching clicks.

Qt can do this with the `WindowTransparentForInput` flag, and that is what we
use everywhere except Windows. On Windows, changing that flag on a window that
is already showing is not dependable, so there we set the `WS_EX_TRANSPARENT`
extended window style ourselves, in place, with no window re-creation.

!! The Win32 part has NOT been verified on a real desktop by hand. The style
arithmetic is unit tested, and a Windows-only test checks that the style bit
really flips on a real window.
"""

import sys
from typing import Any, Protocol

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020


def click_through_style(exstyle: int, enabled: bool) -> int:
    """The extended style with click-through switched on or off."""
    if enabled:
        return exstyle | WS_EX_TRANSPARENT | WS_EX_LAYERED
    return exstyle & ~WS_EX_TRANSPARENT  # stay layered: the window is translucent


def is_click_through(exstyle: int) -> bool:
    return bool(exstyle & WS_EX_TRANSPARENT)


def get_exstyle(hwnd: int) -> int:
    """The window's extended style (Windows only)."""
    return _api().get(hwnd)


def set_native_click_through(hwnd: int, enabled: bool) -> int:
    """Set or clear WS_EX_TRANSPARENT on a window. Returns the new style."""
    api = _api()
    new = click_through_style(api.get(hwnd), enabled)
    api.set(hwnd, new)
    return new


class _Api:
    """The few user32 calls we need, with the 64-bit-safe signatures."""

    # Declared here so the type checker sees them on every platform: on Linux it
    # treats the rest of __init__ as unreachable after the platform check.
    _wintypes: Any
    _user32: Any
    _get: Any
    _set: Any

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise OSError("native click-through only works on Windows")
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        get = getattr(user32, "GetWindowLongPtrW", None) or user32.GetWindowLongW
        set_ = getattr(user32, "SetWindowLongPtrW", None) or user32.SetWindowLongW
        get.argtypes = [wintypes.HWND, ctypes.c_int]
        get.restype = ctypes.c_ssize_t
        set_.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        set_.restype = ctypes.c_ssize_t
        user32.SetWindowPos.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        user32.SetWindowPos.restype = wintypes.BOOL
        self._wintypes = wintypes
        self._user32 = user32
        self._get = get
        self._set = set_

    def get(self, hwnd: int) -> int:
        return int(self._get(self._wintypes.HWND(hwnd), GWL_EXSTYLE)) & 0xFFFFFFFF

    def set(self, hwnd: int, style: int) -> None:
        handle = self._wintypes.HWND(hwnd)
        self._set(handle, GWL_EXSTYLE, style)
        # make Windows pick up the new style without moving or activating
        self._user32.SetWindowPos(
            handle,
            None,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        )


def _api() -> _Api:
    return _Api()


class ClickThrough(Protocol):
    """How a window is switched between click-through and catching clicks."""

    # True if the style is lost when the window is shown again and must be reapplied.
    reapply_on_show: bool

    def apply(self, window: QWidget, enabled: bool) -> None: ...


class QtFlagClickThrough:
    """Everywhere except Windows: the Qt window flag."""

    reapply_on_show = False

    def apply(self, window: QWidget, enabled: bool) -> None:
        was_visible = window.isVisible()  # asked first: changing flags hides it
        window.setWindowFlag(Qt.WindowType.WindowTransparentForInput, enabled)
        if was_visible:
            window.show()


class Win32ClickThrough:
    """Windows: set WS_EX_TRANSPARENT directly, in place."""

    reapply_on_show = True

    def apply(self, window: QWidget, enabled: bool) -> None:
        set_native_click_through(int(window.winId()), enabled)


def default_click_through(platform_name: str) -> ClickThrough:
    """The right switch for this platform. `platform_name` is Qt's platform
    plugin name: only the real Windows plugin has window handles we can use
    (the offscreen plugin used in tests does not)."""
    if sys.platform == "win32" and platform_name == "windows":
        return Win32ClickThrough()
    return QtFlagClickThrough()
