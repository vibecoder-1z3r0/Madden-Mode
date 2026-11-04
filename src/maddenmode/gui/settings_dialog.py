"""Settings dialog: hotkeys, fade-all time and the pens' own settings.

The widgets' ranges already match the limits in Pen and Settings, so the
values it returns are always valid.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from maddenmode.controller import ModifierPrefix, Settings
from maddenmode.labels import mode_label
from maddenmode.pen import MAX_TIME_S, DissipationMode, Pen

COLUMNS = ["Pen", "Width (px)", "Feather (px)", "Mode", "Hold (s)", "Fade (s)"]


def _spin(
    value: float, low: float, high: float, step: float, suffix: str = ""
) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(low, high)
    spin.setSingleStep(step)
    spin.setDecimals(1)
    spin.setSuffix(suffix)
    spin.setValue(value)
    return spin


class SettingsDialog(QDialog):
    def __init__(
        self,
        settings: Settings,
        pens: tuple[Pen, ...],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Madden Mode settings")
        # the overlay and toolbar are always on top; stay above them
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self._pens = pens

        layout = QVBoxLayout(self)

        general = QGroupBox("General")
        form = QFormLayout(general)
        self.prefix_combo = QComboBox()
        for prefix in ModifierPrefix:
            self.prefix_combo.addItem(str(prefix), prefix)
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
        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result_values(self) -> tuple[Settings, tuple[Pen, ...]]:
        """The settings and pens as currently entered."""
        settings = Settings(
            prefix=self.prefix_combo.currentData(),
            hold_to_draw=self.hold_check.isChecked(),
            fade_all_s=self.fade_all_spin.value(),
        )
        pens = tuple(
            Pen(
                name=pen.name,
                color=pen.color,
                width=self.width_spins[i].value(),
                feather=self.feather_spins[i].value(),
                mode=self.mode_combos[i].currentData(),
                hold_s=self.hold_spins[i].value(),
                fade_s=self.fade_spins[i].value(),
            )
            for i, pen in enumerate(self._pens)
        )
        return settings, pens
