"""Pick where to draw: one of the monitors, or a window to pin the overlay to."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from maddenmode.targeting import (
    MonitorTarget,
    ScreenInfo,
    Target,
    WindowTarget,
    resolve_monitor,
)
from maddenmode.windows import WindowBackend

DATA = Qt.ItemDataRole.UserRole


class TargetDialog(QDialog):
    def __init__(
        self,
        screens: list[ScreenInfo],
        backend: WindowBackend,
        current: Target,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Where to draw")
        # the overlay and toolbar are always on top; stay above them
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.backend = backend
        self.resize(520, 520)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Draw over a whole monitor:"))
        self.monitor_list = QListWidget()
        selected_monitor = None
        if isinstance(current, MonitorTarget) and screens:
            selected_monitor = resolve_monitor(current.index, screens)[0].index
        for screen in screens:
            item = QListWidgetItem(screen.label())
            item.setData(DATA, screen.index)
            self.monitor_list.addItem(item)
            if screen.index == selected_monitor:
                self.monitor_list.setCurrentItem(item)
        layout.addWidget(self.monitor_list)

        row = QHBoxLayout()
        row.addWidget(QLabel("...or pin the overlay to a window:"))
        row.addStretch()
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_windows)
        row.addWidget(self.refresh_button)
        layout.addLayout(row)

        self.window_list = QListWidget()
        layout.addWidget(self.window_list)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        # only one of the two lists can hold the choice
        self.monitor_list.itemSelectionChanged.connect(
            lambda: self._clear_other(self.window_list, self.monitor_list)
        )
        self.window_list.itemSelectionChanged.connect(
            lambda: self._clear_other(self.monitor_list, self.window_list)
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._current = current
        self.refresh_windows()

    @staticmethod
    def _clear_other(other: QListWidget, chosen: QListWidget) -> None:
        if chosen.selectedItems():
            other.blockSignals(True)
            other.clearSelection()
            other.blockSignals(False)

    def refresh_windows(self) -> None:
        self.window_list.clear()
        if not self.backend.available:
            self.window_list.setEnabled(False)
            self.refresh_button.setEnabled(False)
            self.status.setText(
                "Pinning to a window is only available on Windows for now. "
                "Choose a monitor instead."
            )
            return
        windows = sorted(self.backend.list_windows(), key=lambda w: w.title.lower())
        for window in windows:
            item = QListWidgetItem(
                f"{window.title}   ({window.rect.width}x{window.rect.height})"
            )
            item.setData(DATA, (window.handle, window.title))
            self.window_list.addItem(item)
            if (
                isinstance(self._current, WindowTarget)
                and self._current.handle == window.handle
            ):
                self.window_list.setCurrentItem(item)
        self.status.setText(
            f"{len(windows)} windows found. The overlay follows the window you pick "
            "and hides while it is minimized."
            if windows
            else "No windows found. Open the app or game, then press Refresh."
        )

    def result_target(self) -> Target | None:
        """What is selected, or None if nothing is."""
        monitor = self.monitor_list.selectedItems()
        if monitor:
            return MonitorTarget(int(monitor[0].data(DATA)))
        window = self.window_list.selectedItems()
        if window:
            handle, title = window[0].data(DATA)
            return WindowTarget(int(handle), str(title))
        return None
