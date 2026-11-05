"""Settings dialog: hotkeys, fade-all time and the pens' own settings.

The widgets' ranges already match the limits in Pen and Settings, so the
values it returns are always valid.
"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from maddenmode.controller import ModifierPrefix, Settings
from maddenmode.labels import display_chord, mode_label
from maddenmode.pen import DEFAULT_PENS, MAX_TIME_S, DissipationMode, Pen

COLUMNS = ["Pen", "Width (px)", "Feather (px)", "Mode", "Hold (s)", "Fade (s)"]

DEFAULT_SIZE = (940, 580)
MIN_SIZE = (780, 460)
ROW_HEIGHT = 46
CONTROL_HEIGHT = 32


def fit_size(desired: tuple[int, int], available: tuple[int, int]) -> tuple[int, int]:
    """`desired`, but no bigger than 90% of the space on the screen."""
    return (
        min(desired[0], int(available[0] * 0.9)),
        min(desired[1], int(available[1] * 0.9)),
    )


def _spin(
    value: float, low: float, high: float, step: float, suffix: str = ""
) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(low, high)
    spin.setSingleStep(step)
    spin.setDecimals(1)
    spin.setSuffix(suffix)
    spin.setValue(value)
    spin.setMinimumHeight(CONTROL_HEIGHT)
    return spin


class SettingsDialog(QDialog):
    def __init__(
        self,
        settings: Settings,
        pens: tuple[Pen, ...],
        parent: QWidget | None = None,
        platform: str = sys.platform,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Madden Mode settings")
        # the overlay and toolbar are always on top; stay above them
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self._pens = pens
        # The dialog does not edit these, but they must survive pressing OK.
        self._monitor = settings.monitor

        self.setMinimumSize(*MIN_SIZE)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            self.resize(
                *fit_size(DEFAULT_SIZE, (available.width(), available.height()))
            )
        else:
            self.resize(*DEFAULT_SIZE)

        layout = QVBoxLayout(self)

        general = QGroupBox("General")
        form = QFormLayout(general)
        self.prefix_combo = QComboBox()
        self.prefix_combo.setMinimumHeight(CONTROL_HEIGHT)
        for prefix in ModifierPrefix:
            # shown as Cmd/Option on macOS; the value stays the ModifierPrefix
            self.prefix_combo.addItem(display_chord(str(prefix), platform), prefix)
        self.prefix_combo.setCurrentIndex(list(ModifierPrefix).index(settings.prefix))
        form.addRow("Global hotkey prefix", self.prefix_combo)
        self.hold_check = QCheckBox("Draw only while the draw key is held")
        self.hold_check.setChecked(settings.hold_to_draw)
        form.addRow("Hold to draw", self.hold_check)
        self.fade_all_spin = _spin(settings.fade_all_s, 0.0, MAX_TIME_S, 0.1, " s")
        form.addRow("Fade-all time (0 = instant)", self.fade_all_spin)
        layout.addWidget(general)

        layout.addWidget(QLabel("Pens (a fade of 0 s means the pen never fades)"))
        self.table = QTableWidget(len(pens), len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.width_spins: list[QDoubleSpinBox] = []
        self.feather_spins: list[QDoubleSpinBox] = []
        self.mode_combos: list[QComboBox] = []
        self.hold_spins: list[QDoubleSpinBox] = []
        self.fade_spins: list[QDoubleSpinBox] = []
        for row, pen in enumerate(pens):
            self.table.setCellWidget(row, 0, QLabel(f"  {pen.name} ({pen.color.name})"))
            width = _spin(pen.width, 1.0, 200.0, 1.0)
            feather = _spin(pen.feather, 0.0, 50.0, 0.5)
            mode = QComboBox()
            mode.setMinimumHeight(CONTROL_HEIGHT)
            for m in DissipationMode:
                mode.addItem(mode_label(m), m)
            mode.setCurrentIndex(list(DissipationMode).index(pen.mode))
            hold = _spin(pen.hold_s, 0.0, MAX_TIME_S, 0.1)
            fade = _spin(pen.fade_s, 0.0, MAX_TIME_S, 0.1)
            for column, widget in enumerate(
                (width, feather, mode, hold, fade), start=1
            ):
                self.table.setCellWidget(row, column, widget)
            self.width_spins.append(width)
            self.feather_spins.append(feather)
            self.mode_combos.append(mode)
            self.hold_spins.append(hold)
            self.fade_spins.append(fade)
        # roomy rows, and the columns share the width instead of being cramped
        self.table.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)  # takes any extra height

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )
        reset = buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults)
        reset.setText("Reset to defaults")
        reset.clicked.connect(self.reset_to_defaults)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def reset_to_defaults(self) -> None:
        """Put the default values into the form. Nothing is saved until OK."""
        defaults = Settings()
        self.prefix_combo.setCurrentIndex(list(ModifierPrefix).index(defaults.prefix))
        self.hold_check.setChecked(defaults.hold_to_draw)
        self.fade_all_spin.setValue(defaults.fade_all_s)
        by_name = {pen.name: pen for pen in DEFAULT_PENS}
        for row, pen in enumerate(self._pens):
            default = by_name.get(pen.name)
            if default is None:
                continue  # a pen we have no default for: leave it as it is
            self.width_spins[row].setValue(default.width)
            self.feather_spins[row].setValue(default.feather)
            self.mode_combos[row].setCurrentIndex(
                list(DissipationMode).index(default.mode)
            )
            self.hold_spins[row].setValue(default.hold_s)
            self.fade_spins[row].setValue(default.fade_s)

    def result_values(self) -> tuple[Settings, tuple[Pen, ...]]:
        """The settings and pens as currently entered."""
        settings = Settings(
            # Qt hands enum values back as plain strings: turn them back into enums
            prefix=ModifierPrefix(self.prefix_combo.currentData()),
            hold_to_draw=self.hold_check.isChecked(),
            fade_all_s=self.fade_all_spin.value(),
            monitor=self._monitor,
        )
        pens = tuple(
            Pen(
                name=pen.name,
                color=pen.color,
                width=self.width_spins[i].value(),
                feather=self.feather_spins[i].value(),
                mode=DissipationMode(self.mode_combos[i].currentData()),
                hold_s=self.hold_spins[i].value(),
                fade_s=self.fade_spins[i].value(),
            )
            for i, pen in enumerate(self._pens)
        )
        return settings, pens
