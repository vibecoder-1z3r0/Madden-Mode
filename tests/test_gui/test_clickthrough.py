import json
import os
import subprocess
import sys

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

from maddenmode.controller import Controller
from maddenmode.gui import clickthrough as ct
from maddenmode.gui import overlay as overlay_module
from maddenmode.gui.overlay import OverlayWindow
from maddenmode.scene import Scene

# -- the style arithmetic (pure) ---------------------------------------------


def test_enabling_sets_transparent_and_layered() -> None:
    style = ct.click_through_style(0, True)
    assert style & ct.WS_EX_TRANSPARENT
    assert style & ct.WS_EX_LAYERED


def test_disabling_clears_transparent_but_stays_layered() -> None:
    style = ct.click_through_style(ct.WS_EX_TRANSPARENT | ct.WS_EX_LAYERED, False)
    assert not style & ct.WS_EX_TRANSPARENT
    assert style & ct.WS_EX_LAYERED


def test_other_style_bits_are_left_alone() -> None:
    other = 0x08000000 | 0x00000080  # WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
    on = ct.click_through_style(other, True)
    assert on & other == other
    assert ct.click_through_style(on, False) & other == other


def test_switching_twice_is_stable() -> None:
    once = ct.click_through_style(0, True)
    assert ct.click_through_style(once, True) == once
    off = ct.click_through_style(once, False)
    assert ct.click_through_style(off, False) == off


def test_is_click_through_reads_the_bit() -> None:
    assert ct.is_click_through(ct.WS_EX_TRANSPARENT)
    assert not ct.is_click_through(ct.WS_EX_LAYERED)


@pytest.mark.skipif(sys.platform == "win32", reason="checks the non-Windows refusal")
def test_native_calls_refuse_other_platforms() -> None:
    with pytest.raises(OSError):
        ct.get_exstyle(1)
    with pytest.raises(OSError):
        ct.set_native_click_through(1, True)


def test_the_qt_flag_switch_is_used_off_windows_and_for_offscreen() -> None:
    assert isinstance(ct.default_click_through("offscreen"), ct.QtFlagClickThrough)
    assert isinstance(ct.default_click_through("xcb"), ct.QtFlagClickThrough)
    if sys.platform != "win32":  # on Windows the real plugin picks the native one
        assert isinstance(ct.default_click_through("windows"), ct.QtFlagClickThrough)


def test_the_qt_flag_switch_keeps_a_visible_window_visible(qapp: QApplication) -> None:
    widget = QWidget()
    widget.show()
    switch = ct.QtFlagClickThrough()
    switch.apply(widget, True)
    assert widget.isVisible()  # changing the flag hides it; apply must re-show it
    assert widget.windowFlags() & Qt.WindowType.WindowTransparentForInput
    switch.apply(widget, False)
    assert widget.isVisible()
    assert not widget.windowFlags() & Qt.WindowType.WindowTransparentForInput
    widget.close()


# -- how the overlay uses a switch (with a fake one) ---------------------------


class FakeSwitch:
    def __init__(self, reapply_on_show: bool) -> None:
        self.reapply_on_show = reapply_on_show
        self.calls: list[bool] = []

    def apply(self, window: QWidget, enabled: bool) -> None:
        self.calls.append(enabled)


def overlay_with(switch: FakeSwitch) -> tuple[OverlayWindow, Controller]:
    controller = Controller(Scene())
    window = OverlayWindow(controller, click_through=switch)
    return window, controller


def test_a_flag_style_switch_starts_click_through_at_construction(
    qapp: QApplication,
) -> None:
    switch = FakeSwitch(reapply_on_show=False)
    overlay_with(switch)
    assert switch.calls == [True]


def test_a_native_style_switch_waits_for_the_window_to_exist(
    qapp: QApplication,
) -> None:
    switch = FakeSwitch(reapply_on_show=True)
    window, _ = overlay_with(switch)
    assert switch.calls == []  # no window handle yet: nothing to set
    window.show()
    assert switch.calls == [True]  # applied as soon as it shows, click-through
    window.close()


def test_draw_mode_switches_the_overlay_to_catch_clicks_and_back(
    qapp: QApplication,
) -> None:
    switch = FakeSwitch(reapply_on_show=True)
    window, controller = overlay_with(switch)
    window.show()
    switch.calls.clear()
    controller.set_draw_mode(True, 0.0)
    controller.set_draw_mode(False, 1.0)
    assert switch.calls == [False, True]
    window.close()


def test_a_native_switch_is_reapplied_every_time_the_window_shows(
    qapp: QApplication,
) -> None:
    switch = FakeSwitch(reapply_on_show=True)
    window, controller = overlay_with(switch)
    window.show()
    controller.set_draw_mode(True, 0.0)
    switch.calls.clear()
    window.hide()
    window.show()  # e.g. after a pinned window was minimized and restored
    assert switch.calls == [False]  # still catching clicks, not reset to click-through
    window.close()


def test_a_flag_style_switch_is_not_reapplied_on_show(qapp: QApplication) -> None:
    switch = FakeSwitch(reapply_on_show=False)
    window, _ = overlay_with(switch)
    switch.calls.clear()
    window.show()
    window.hide()
    window.show()
    assert switch.calls == []  # re-applying would recurse: it changes flags
    window.close()


# -- diagnostics and tuning -----------------------------------------------------


def test_debug_output_is_off_by_default(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    monkeypatch.delenv("MADDEN_DEBUG", raising=False)
    window, controller = overlay_with(FakeSwitch(False))
    controller.set_draw_mode(True, 0.0)
    assert "[madden]" not in capsys.readouterr().err
    window.close()


def test_debug_output_describes_the_window_when_asked(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    monkeypatch.setenv("MADDEN_DEBUG", "1")
    window, controller = overlay_with(FakeSwitch(False))
    window.show()
    controller.set_draw_mode(True, 0.0)
    err = capsys.readouterr().err
    assert "[madden] draw_mode=True" in err
    assert "switch=FakeSwitch" in err
    assert "hit_alpha=" in err
    assert "qt_platform=" in err
    window.close()


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, 2), ("10", 10), ("0", 1), ("-5", 1), ("999", 255), ("abc", 2), ("", 2)],
)
def test_the_hit_alpha_can_be_overridden_safely(
    monkeypatch: pytest.MonkeyPatch, value: str | None, expected: int
) -> None:
    if value is None:
        monkeypatch.delenv("MADDEN_HIT_ALPHA", raising=False)
    else:
        monkeypatch.setenv("MADDEN_HIT_ALPHA", value)
    assert overlay_module._hit_alpha() == expected


# -- on a real Windows window (runs on the Windows CI runner only) --------------

REAL_WINDOW_SCRIPT = """
import json
from PySide6.QtWidgets import QApplication
from maddenmode.controller import Controller
from maddenmode.gui import clickthrough as ct
from maddenmode.gui.overlay import OverlayWindow
from maddenmode.scene import Scene

app = QApplication([])
controller = Controller(Scene())
window = OverlayWindow(controller)
window.resize(200, 100)
window.show()
app.processEvents()

def click_through():
    return ct.is_click_through(ct.get_exstyle(int(window.winId())))

out = {"platform": app.platformName(), "switch": type(window.click_through).__name__}
out["at_start"] = click_through()
controller.set_draw_mode(True, 0.0)
app.processEvents()
out["while_drawing"] = click_through()
controller.set_draw_mode(False, 1.0)
app.processEvents()
out["after_drawing"] = click_through()
controller.set_draw_mode(True, 2.0)
window.hide()
window.show()
app.processEvents()
out["drawing_after_reshow"] = click_through()
print("RESULT " + json.dumps(out))
"""


@pytest.mark.skipif(sys.platform != "win32", reason="needs a real Windows window")
def test_the_real_windows_style_really_flips() -> None:
    env = {**os.environ, "QT_QPA_PLATFORM": "windows"}
    result = subprocess.run(
        [sys.executable, "-c", REAL_WINDOW_SCRIPT],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    lines = [x for x in result.stdout.splitlines() if x.startswith("RESULT ")]
    assert lines, f"no result; stdout={result.stdout!r} stderr={result.stderr!r}"
    got = json.loads(lines[0][len("RESULT ") :])
    assert got["platform"] == "windows"
    assert got["switch"] == "Win32ClickThrough"
    assert got["at_start"] is True  # click-through until drawing
    assert got["while_drawing"] is False  # catches the mouse while drawing
    assert got["after_drawing"] is True  # click-through again
    assert got["drawing_after_reshow"] is False  # survives hide and show
