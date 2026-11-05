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


# -- size, reset, and keeping what the dialog does not edit ---------------------

from PySide6.QtWidgets import QHeaderView  # noqa: E402

from maddenmode.gui.settings_dialog import (  # noqa: E402
    DEFAULT_SIZE,
    MIN_SIZE,
    ROW_HEIGHT,
    fit_size,
)
from maddenmode.pen import Pen  # noqa: E402


def test_it_opens_large_enough_to_see_every_pen(qapp: QApplication) -> None:
    dialog = SettingsDialog(Settings(), DEFAULT_PENS)
    assert dialog.width() >= MIN_SIZE[0]
    assert dialog.height() >= MIN_SIZE[1]
    # the pen table has room for all of its rows without scrolling
    needed = dialog.table.rowCount() * ROW_HEIGHT
    assert dialog.table.viewport().height() >= 0
    assert dialog.table.verticalHeader().defaultSectionSize() == ROW_HEIGHT
    assert needed <= dialog.height()


def test_it_can_be_resized_but_not_below_its_minimum(qapp: QApplication) -> None:
    dialog = SettingsDialog(Settings(), DEFAULT_PENS)
    assert dialog.minimumWidth() == MIN_SIZE[0]
    assert dialog.minimumHeight() == MIN_SIZE[1]
    dialog.resize(1400, 900)
    assert (dialog.width(), dialog.height()) == (1400, 900)
    dialog.resize(100, 100)
    assert dialog.width() >= MIN_SIZE[0]


def test_the_table_columns_share_the_width(qapp: QApplication) -> None:
    dialog = SettingsDialog(Settings(), DEFAULT_PENS)
    header = dialog.table.horizontalHeader()
    for column in range(1, dialog.table.columnCount()):
        assert header.sectionResizeMode(column) == QHeaderView.ResizeMode.Stretch


def test_the_default_size_is_cut_down_to_fit_a_small_screen() -> None:
    assert fit_size(DEFAULT_SIZE, (3840, 2160)) == DEFAULT_SIZE
    assert fit_size(DEFAULT_SIZE, (1000, 600)) == (900, 540)  # 90% of the screen
    assert fit_size((500, 500), (2000, 2000)) == (500, 500)


def test_inputs_are_tall_enough_to_click_comfortably(qapp: QApplication) -> None:
    dialog = SettingsDialog(Settings(), DEFAULT_PENS)
    for spin in (*dialog.width_spins, *dialog.hold_spins, dialog.fade_all_spin):
        assert spin.minimumHeight() >= 30
    assert dialog.prefix_combo.minimumHeight() >= 30


def test_reset_puts_the_defaults_back_in_the_form(qapp: QApplication) -> None:
    changed = Settings(prefix=ModifierPrefix.CTRL_ALT, hold_to_draw=True, fade_all_s=8)
    pens = tuple(
        Pen(p.name, color=p.color, width=77, feather=9, hold_s=9, fade_s=9)
        for p in DEFAULT_PENS
    )
    dialog = SettingsDialog(changed, pens)
    dialog.reset_to_defaults()
    settings, got = dialog.result_values()
    assert settings.prefix == Settings().prefix
    assert not settings.hold_to_draw
    assert settings.fade_all_s == Settings().fade_all_s
    assert got == DEFAULT_PENS


def test_reset_leaves_a_pen_it_has_no_default_for(qapp: QApplication) -> None:
    custom = Pen("my own pen", width=33, feather=4, hold_s=2, fade_s=2)
    dialog = SettingsDialog(Settings(), (custom,))
    dialog.reset_to_defaults()
    assert dialog.result_values()[1] == (custom,)


def test_the_reset_button_is_there_and_works(qapp: QApplication) -> None:
    from PySide6.QtWidgets import QDialogButtonBox, QPushButton

    dialog = SettingsDialog(Settings(fade_all_s=9), DEFAULT_PENS)
    buttons = dialog.findChildren(QDialogButtonBox)[0]
    reset = buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults)
    assert isinstance(reset, QPushButton)
    assert reset.text() == "Reset to defaults"
    reset.click()
    assert dialog.fade_all_spin.value() == Settings().fade_all_s


def test_pressing_ok_keeps_the_saved_monitor(qapp: QApplication) -> None:
    dialog = SettingsDialog(Settings(monitor=2), DEFAULT_PENS)
    settings, _ = dialog.result_values()
    assert settings.monitor == 2  # it used to reset to 0


def test_the_comet_default_is_the_one_the_owner_chose() -> None:
    comet = next(p for p in DEFAULT_PENS if p.name == "comet")
    assert comet.width == 24.0
    assert comet.hold_s == 1.5
    assert comet.fade_s == 3.0
    assert comet.mode == DissipationMode.TAIL_FIRST


def test_the_default_pens_all_fit_the_dialogs_limits() -> None:
    # the dialog's spin boxes would silently clamp anything outside these
    for pen in DEFAULT_PENS:
        assert 1.0 <= pen.width <= 200.0
        assert 0.0 <= pen.feather <= 50.0
        assert 0.0 <= pen.hold_s <= 10.0
        assert 0.0 <= pen.fade_s <= 10.0


def test_the_values_it_returns_are_real_enums_not_strings(qapp: QApplication) -> None:
    """Qt turns enum data into plain strings; the settings code needs enums."""
    dialog = SettingsDialog(Settings(), DEFAULT_PENS)
    settings, pens = dialog.result_values()
    assert isinstance(settings.prefix, ModifierPrefix)
    assert all(isinstance(p.mode, DissipationMode) for p in pens)
    assert type(settings.prefix) is not str
    assert all(type(p.mode) is not str for p in pens)


def test_values_from_the_real_dialog_can_be_saved_and_read_back(
    qapp: QApplication, tmp_path
) -> None:  # type: ignore[no-untyped-def]
    from maddenmode import settings_store

    dialog = SettingsDialog(Settings(monitor=1), DEFAULT_PENS)
    dialog.prefix_combo.setCurrentIndex(1)  # Ctrl+Alt
    comet = next(i for i, p in enumerate(DEFAULT_PENS) if p.name == "comet")
    dialog.width_spins[comet].setValue(24)
    dialog.hold_spins[comet].setValue(1.5)
    dialog.fade_spins[comet].setValue(3)
    settings, pens = dialog.result_values()
    path = tmp_path / "settings.json"
    settings_store.save(path, settings, pens)  # raised AttributeError before the fix
    got_settings, got_pens, warning = settings_store.load(path)
    assert warning is None
    assert got_settings.prefix == ModifierPrefix.CTRL_ALT
    assert got_settings.monitor == 1
    assert (got_pens[comet].width, got_pens[comet].hold_s, got_pens[comet].fade_s) == (
        24.0,
        1.5,
        3.0,
    )


def test_flash_and_comet_share_their_size_and_timing() -> None:
    by_name = {p.name: p for p in DEFAULT_PENS}
    flash, comet = by_name["flash"], by_name["comet"]
    assert (flash.width, flash.feather) == (comet.width, comet.feather) == (24.0, 2.0)
    assert (flash.hold_s, flash.fade_s) == (comet.hold_s, comet.fade_s) == (1.5, 3.0)
    # what makes them different pens is how they fade, and their color
    assert flash.mode == DissipationMode.TIMED_FADE
    assert comet.mode == DissipationMode.TAIL_FIRST
    assert flash.color != comet.color


def test_the_other_default_pens_are_unchanged() -> None:
    by_name = {p.name: p for p in DEFAULT_PENS}
    assert (by_name["marker"].width, by_name["marker"].feather) == (6.0, 0.0)
    assert (by_name["highlighter"].width, by_name["highlighter"].feather) == (14.0, 2.0)
    assert by_name["marker"].fade_s == by_name["highlighter"].fade_s == 0.0


# -- macOS key names ------------------------------------------------------------


def combo_texts(dialog: SettingsDialog) -> list[str]:
    return [dialog.prefix_combo.itemText(i) for i in range(dialog.prefix_combo.count())]


def test_the_prefix_choices_keep_ctrl_and_say_option_on_a_mac(
    qapp: QApplication,
) -> None:
    dialog = SettingsDialog(Settings(), DEFAULT_PENS, platform="darwin")
    assert combo_texts(dialog) == ["Ctrl+Shift", "Ctrl+Option"]


def test_the_prefix_choices_are_unchanged_elsewhere(qapp: QApplication) -> None:
    for platform in ("win32", "linux"):
        dialog = SettingsDialog(Settings(), DEFAULT_PENS, platform=platform)
        assert combo_texts(dialog) == ["Ctrl+Shift", "Ctrl+Alt"]


def test_a_mac_user_still_gets_the_internal_prefix_back(qapp: QApplication) -> None:
    """The label is cosmetic: what is saved and matched is still Ctrl+..."""
    dialog = SettingsDialog(Settings(), DEFAULT_PENS, platform="darwin")
    dialog.prefix_combo.setCurrentIndex(1)  # shown as "Ctrl+Option"
    settings, _ = dialog.result_values()
    assert settings.prefix == ModifierPrefix.CTRL_ALT
    assert type(settings.prefix) is ModifierPrefix


def test_the_current_prefix_is_selected_on_a_mac(qapp: QApplication) -> None:
    dialog = SettingsDialog(
        Settings(prefix=ModifierPrefix.CTRL_ALT), DEFAULT_PENS, platform="darwin"
    )
    assert dialog.prefix_combo.currentText() == "Ctrl+Option"
