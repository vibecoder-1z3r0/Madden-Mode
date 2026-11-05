from PySide6.QtWidgets import QApplication

from maddenmode.gui.target_dialog import TargetDialog
from maddenmode.targeting import (
    MonitorTarget,
    Rect,
    ScreenInfo,
    Target,
    WindowTarget,
)
from maddenmode.windows import NullWindowBackend, WindowInfo, WindowState

SCREENS = [
    ScreenInfo(0, "Left", Rect(0, 0, 1920, 1080), 1.0, primary=True),
    ScreenInfo(1, "Right", Rect(1920, 0, 2560, 1440), 1.0),
]


class FakeBackend:
    available = True

    def __init__(self, windows: list[WindowInfo]) -> None:
        self.windows = windows

    def list_windows(self) -> list[WindowInfo]:
        return list(self.windows)

    def get_state(self, handle: int) -> WindowState:
        raise AssertionError("the dialog only lists windows")


WINDOWS = [
    WindowInfo(11, "zebra game", Rect(0, 0, 800, 600)),
    WindowInfo(12, "Alpha app", Rect(10, 10, 1000, 700)),
]


def make(
    current: Target | None = None, windows: list[WindowInfo] | None = None
) -> TargetDialog:
    return TargetDialog(
        SCREENS,
        FakeBackend(WINDOWS if windows is None else windows),
        current if current is not None else MonitorTarget(0),
    )


def test_lists_every_monitor_with_the_current_one_selected(qapp: QApplication) -> None:
    dialog = make(MonitorTarget(1))
    assert dialog.monitor_list.count() == 2
    assert "Right" in dialog.monitor_list.item(1).text()
    assert dialog.result_target() == MonitorTarget(1)


def test_a_missing_current_monitor_selects_the_primary(qapp: QApplication) -> None:
    assert make(MonitorTarget(9)).result_target() == MonitorTarget(0)


def test_lists_windows_sorted_case_insensitively(qapp: QApplication) -> None:
    dialog = make()
    titles = [
        dialog.window_list.item(i).text() for i in range(dialog.window_list.count())
    ]
    assert titles[0].startswith("Alpha app")
    assert titles[1].startswith("zebra game")
    assert "1000x700" in titles[0]


def test_picking_a_window_returns_a_window_target(qapp: QApplication) -> None:
    dialog = make()
    dialog.window_list.setCurrentRow(1)  # "zebra game"
    assert dialog.result_target() == WindowTarget(11, "zebra game")


def test_only_one_list_holds_the_choice(qapp: QApplication) -> None:
    dialog = make()
    dialog.window_list.setCurrentRow(0)
    assert not dialog.monitor_list.selectedItems()
    dialog.monitor_list.setCurrentRow(1)
    assert not dialog.window_list.selectedItems()
    assert dialog.result_target() == MonitorTarget(1)


def test_the_current_pinned_window_is_preselected(qapp: QApplication) -> None:
    dialog = make(WindowTarget(12, "Alpha app"))
    assert dialog.result_target() == WindowTarget(12, "Alpha app")
    assert not dialog.monitor_list.selectedItems()


def test_nothing_selected_gives_none(qapp: QApplication) -> None:
    dialog = make(WindowTarget(404, "closed window"))  # not in the list
    assert dialog.result_target() is None


def test_refresh_picks_up_new_windows(qapp: QApplication) -> None:
    backend = FakeBackend(WINDOWS[:1])
    dialog = TargetDialog(SCREENS, backend, MonitorTarget(0))
    assert dialog.window_list.count() == 1
    backend.windows = list(WINDOWS)
    dialog.refresh_windows()
    assert dialog.window_list.count() == 2


def test_no_windows_says_what_to_do(qapp: QApplication) -> None:
    dialog = make(windows=[])
    assert dialog.window_list.count() == 0
    assert "Refresh" in dialog.status.text()


def test_without_window_support_it_explains_and_still_offers_monitors(
    qapp: QApplication,
) -> None:
    dialog = TargetDialog(SCREENS, NullWindowBackend(), MonitorTarget(0))
    assert not dialog.window_list.isEnabled()
    assert not dialog.refresh_button.isEnabled()
    assert "Windows" in dialog.status.text()
    assert dialog.result_target() == MonitorTarget(0)


def test_stays_above_the_always_on_top_overlay(qapp: QApplication) -> None:
    from PySide6.QtCore import Qt

    assert make().windowFlags() & Qt.WindowType.WindowStaysOnTopHint
