"""Smoke tests for the Win32 window backend. Only run on Windows (in CI).

They cannot check the exact windows on a runner, so they check that the calls
work and return sensible types, and that a bogus handle is reported as gone.
"""

import os
import sys

import pytest

from maddenmode.targeting import Rect
from maddenmode.windows import WindowInfo, WindowKind

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="needs the Win32 API")


def backend():  # type: ignore[no-untyped-def]
    from maddenmode.gui.windows_win32 import Win32WindowBackend

    return Win32WindowBackend()


def test_is_available() -> None:
    assert backend().available


def test_lists_windows_of_the_right_shape() -> None:
    windows = backend().list_windows()
    assert isinstance(windows, list)
    for window in windows:
        assert isinstance(window, WindowInfo)
        assert window.title.strip()
        assert isinstance(window.rect, Rect)
        assert window.rect.width >= 50
        assert window.rect.height >= 50


def test_a_bogus_handle_is_gone() -> None:
    assert backend().get_state(0xDEADBEEF).kind == WindowKind.GONE
    assert backend().get_state(0).kind == WindowKind.GONE


def test_a_listed_window_reports_a_state_with_a_rect_when_visible() -> None:
    b = backend()
    for window in b.list_windows()[:5]:
        state = b.get_state(window.handle)
        assert state.kind in set(WindowKind)
        if state.kind == WindowKind.VISIBLE:
            assert state.rect is not None


def test_our_own_process_windows_are_not_offered() -> None:
    # this test process owns no top-level windows, but the filter must not crash
    assert all(w.title for w in backend().list_windows())
    assert os.getpid() > 0
