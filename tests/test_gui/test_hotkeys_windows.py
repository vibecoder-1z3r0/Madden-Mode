"""Tests for the Win32 hotkey backend. They only run on Windows (in CI)."""

import ctypes
import sys

import pytest
from PySide6.QtWidgets import QApplication

from maddenmode.gui.hotkeys import WM_HOTKEY, WindowsHotkeys

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="needs the Win32 API")

EVENT_TYPE = b"windows_generic_MSG"
# An unusual chord so it is very unlikely to clash with anything on a machine.
CHORD = "Ctrl+Alt+Shift+F11"


def message(code: int, wparam: int) -> "ctypes.wintypes.MSG":
    import ctypes.wintypes

    msg = ctypes.wintypes.MSG()
    msg.message = code
    msg.wParam = wparam
    return msg


def test_dispatches_a_hotkey_message_to_its_callback(qapp: QApplication) -> None:
    hotkeys = WindowsHotkeys()
    called: list[int] = []
    hotkeys._callbacks[7] = lambda: called.append(1)
    msg = message(WM_HOTKEY, 7)
    result = hotkeys.nativeEventFilter(EVENT_TYPE, ctypes.addressof(msg))
    assert result == (True, 0)
    assert called == [1]


def test_ignores_an_unknown_hotkey_id(qapp: QApplication) -> None:
    hotkeys = WindowsHotkeys()
    msg = message(WM_HOTKEY, 99)
    assert hotkeys.nativeEventFilter(EVENT_TYPE, ctypes.addressof(msg)) == (False, 0)


def test_ignores_other_windows_messages(qapp: QApplication) -> None:
    hotkeys = WindowsHotkeys()
    called: list[int] = []
    hotkeys._callbacks[1] = lambda: called.append(1)
    msg = message(0x0001, 1)  # not WM_HOTKEY
    assert hotkeys.nativeEventFilter(EVENT_TYPE, ctypes.addressof(msg)) == (False, 0)
    assert called == []


def test_ignores_other_event_types(qapp: QApplication) -> None:
    hotkeys = WindowsHotkeys()
    msg = message(WM_HOTKEY, 1)
    assert hotkeys.nativeEventFilter(b"xcb_generic_event_t", ctypes.addressof(msg)) == (
        False,
        0,
    )


def test_registers_and_unregisters_a_real_hotkey(qapp: QApplication) -> None:
    hotkeys = WindowsHotkeys()
    hotkeys.register({CHORD: lambda: None})
    assert len(hotkeys._callbacks) == 1
    hotkeys.unregister_all()
    assert hotkeys._callbacks == {}


def test_registering_again_replaces_the_old_hotkeys(qapp: QApplication) -> None:
    hotkeys = WindowsHotkeys()
    hotkeys.register({CHORD: lambda: None})
    hotkeys.register({CHORD: lambda: None})  # must not report a clash with itself
    assert len(hotkeys._callbacks) == 1
    hotkeys.unregister_all()


def test_a_clash_with_another_owner_raises_a_clear_error(qapp: QApplication) -> None:
    first, second = WindowsHotkeys(), WindowsHotkeys()
    first.register({CHORD: lambda: None})
    try:
        with pytest.raises(OSError, match="another app"):
            second.register({CHORD: lambda: None})
    finally:
        first.unregister_all()
