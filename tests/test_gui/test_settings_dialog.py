from PySide6.QtWidgets import QApplication

from maddenmode.controller import ModifierPrefix, Settings
from maddenmode.gui.settings_dialog import SettingsDialog
from maddenmode.pen import DEFAULT_PENS, DissipationMode


def test_shows_the_current_values(qapp: QApplication) -> None:
    settings = Settings(
        prefix=ModifierPrefix.CTRL_ALT, hold_to_draw=True, fade_all_s=4.5
    )
    dialog = SettingsDialog(settings, DEFAULT_PENS)
    assert dialog.prefix_combo.currentData() == ModifierPrefix.CTRL_ALT
    assert dialog.hold_check.isChecked()
    assert dialog.fade_all_spin.value() == 4.5
    assert dialog.table.rowCount() == len(DEFAULT_PENS)


def test_unchanged_dialog_returns_equal_values(qapp: QApplication) -> None:
    settings = Settings()
    dialog = SettingsDialog(settings, DEFAULT_PENS)
    got_settings, got_pens = dialog.result_values()
    assert got_settings == settings
    assert got_pens == DEFAULT_PENS


def test_edits_are_returned(qapp: QApplication) -> None:
    dialog = SettingsDialog(Settings(), DEFAULT_PENS)
    dialog.prefix_combo.setCurrentIndex(1)
    dialog.hold_check.setChecked(True)
    dialog.fade_all_spin.setValue(7.5)
    dialog.width_spins[0].setValue(20)
    dialog.feather_spins[0].setValue(3.5)
    dialog.mode_combos[0].setCurrentIndex(
        list(DissipationMode).index(DissipationMode.TIMED_FADE)
    )
    dialog.hold_spins[0].setValue(2.5)
    dialog.fade_spins[0].setValue(6.0)
    settings, pens = dialog.result_values()
    assert settings.prefix == ModifierPrefix.CTRL_ALT
    assert settings.hold_to_draw
    assert settings.fade_all_s == 7.5
    first = pens[0]
    assert (first.width, first.feather) == (20, 3.5)
    assert first.mode == DissipationMode.TIMED_FADE
    assert (first.hold_s, first.fade_s) == (2.5, 6.0)
    assert pens[0].name == DEFAULT_PENS[0].name  # names and colors are kept
    assert pens[0].color == DEFAULT_PENS[0].color
    assert pens[1:] == DEFAULT_PENS[1:]


def test_inputs_cannot_go_outside_the_allowed_range(qapp: QApplication) -> None:
    dialog = SettingsDialog(Settings(), DEFAULT_PENS)
    dialog.fade_all_spin.setValue(99)
    dialog.hold_spins[0].setValue(99)
    dialog.fade_spins[0].setValue(-5)
    dialog.width_spins[0].setValue(0)
    settings, pens = dialog.result_values()  # would raise if anything were invalid
    assert settings.fade_all_s == 10.0
    assert pens[0].hold_s == 10.0
    assert pens[0].fade_s == 0.0
    assert pens[0].width == 1.0


def test_stays_above_the_always_on_top_overlay(qapp: QApplication) -> None:
    from PySide6.QtCore import Qt

    dialog = SettingsDialog(Settings(), DEFAULT_PENS)
    assert dialog.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
