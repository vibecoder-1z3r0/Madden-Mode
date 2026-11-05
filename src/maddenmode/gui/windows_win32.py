"""Window listing and tracking through the Win32 API.

!! NOT VERIFIED ON A REAL DESKTOP. Written without a Windows machine. The
decisions (which windows to offer, coordinate conversion, following) are
tested elsewhere; only the Win32 calls here are untested beyond a smoke test
that they run and return sensible types on a Windows CI runner.
"""

import os
import sys
from typing import Any

from maddenmode.targeting import Rect
from maddenmode.windows import (
    WindowInfo,
    WindowKind,
    WindowState,
    is_pickable,
)

GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
DWMWA_CLOAKED = 14
DWMWA_EXTENDED_FRAME_BOUNDS = 9


class Win32WindowBackend:  # pragma: no cover  (exercised by Windows-only tests)
    available = True

    # Declared here so the type checker sees them on every platform: on Linux it
    # treats the rest of __init__ as unreachable after the platform check.
    _ctypes: Any
    _wintypes: Any
    _user32: Any
    _dwm: Any
    _pid: int

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise OSError("Win32WindowBackend only works on Windows")
        import ctypes
        from ctypes import wintypes

        self._ctypes = ctypes
        self._wintypes = wintypes
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._dwm = ctypes.WinDLL("dwmapi", use_last_error=True)
        self._pid = os.getpid()

        u = self._user32
        u.IsWindow.argtypes = [wintypes.HWND]
        u.IsWindow.restype = wintypes.BOOL
        u.IsWindowVisible.argtypes = [wintypes.HWND]
        u.IsWindowVisible.restype = wintypes.BOOL
        u.IsIconic.argtypes = [wintypes.HWND]
        u.IsIconic.restype = wintypes.BOOL
        u.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        u.GetWindowTextLengthW.restype = ctypes.c_int
        u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        u.GetWindowTextW.restype = ctypes.c_int
        u.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        u.GetWindowLongW.restype = wintypes.LONG
        u.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        u.GetWindowRect.restype = wintypes.BOOL
        u.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.DWORD),
        ]
        u.GetWindowThreadProcessId.restype = wintypes.DWORD
        self._dwm.DwmGetWindowAttribute.argtypes = [
            wintypes.HWND,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        self._dwm.DwmGetWindowAttribute.restype = ctypes.c_long

    # -- helpers --------------------------------------------------------------

    def _hwnd(self, handle: int) -> object:
        return self._wintypes.HWND(handle)

    def _title(self, hwnd: object) -> str:
        length = self._user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buffer = self._ctypes.create_unicode_buffer(length + 1)
        self._user32.GetWindowTextW(hwnd, buffer, length + 1)
        return str(buffer.value)

    def _cloaked(self, hwnd: object) -> bool:
        value = self._wintypes.DWORD(0)
        result = self._dwm.DwmGetWindowAttribute(
            hwnd, DWMWA_CLOAKED, self._ctypes.byref(value), self._ctypes.sizeof(value)
        )
        return bool(result == 0 and value.value != 0)

    def _rect(self, hwnd: object) -> Rect:
        """The visible frame: GetWindowRect includes invisible resize borders."""
        rect = self._wintypes.RECT()
        result = self._dwm.DwmGetWindowAttribute(
            hwnd,
            DWMWA_EXTENDED_FRAME_BOUNDS,
            self._ctypes.byref(rect),
            self._ctypes.sizeof(rect),
        )
        if result != 0:
            self._user32.GetWindowRect(hwnd, self._ctypes.byref(rect))
        return Rect(
            rect.left,
            rect.top,
            max(0, rect.right - rect.left),
            max(0, rect.bottom - rect.top),
        )

    def _owned_by_us(self, hwnd: object) -> bool:
        pid = self._wintypes.DWORD(0)
        self._user32.GetWindowThreadProcessId(hwnd, self._ctypes.byref(pid))
        return bool(pid.value == self._pid)

    # -- the backend interface ---------------------------------------------

    def list_windows(self) -> list[WindowInfo]:
        found: list[WindowInfo] = []
        wintypes = self._wintypes
        callback_type = self._ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
        )

        def visit(hwnd: object, _lparam: object) -> bool:
            title = self._title(hwnd)
            rect = self._rect(hwnd)
            if is_pickable(
                title=title,
                visible=bool(self._user32.IsWindowVisible(hwnd)),
                minimized=bool(self._user32.IsIconic(hwnd)),
                cloaked=self._cloaked(hwnd),
                tool_window=bool(
                    self._user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW
                ),
                own_process=self._owned_by_us(hwnd),
                rect=rect,
            ):
                found.append(WindowInfo(int(hwnd or 0), title, rect))  # type: ignore[call-overload]
            return True

        self._user32.EnumWindows(callback_type(visit), 0)
        return found

    def get_state(self, handle: int) -> WindowState:
        hwnd = self._hwnd(handle)
        if not self._user32.IsWindow(hwnd):
            return WindowState(WindowKind.GONE)
        if (
            self._user32.IsIconic(hwnd)
            or not self._user32.IsWindowVisible(hwnd)
            or self._cloaked(hwnd)
        ):
            return WindowState(WindowKind.MINIMIZED)
        return WindowState(WindowKind.VISIBLE, self._rect(hwnd))
