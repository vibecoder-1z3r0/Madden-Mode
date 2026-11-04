from pathlib import Path

from PySide6.QtCore import QRect, QTimer
from PySide6.QtWidgets import QApplication, QDialog

from maddenmode import settings_store
from maddenmode.app import MaddenMode, _default_dialog, run_smoke_test
from maddenmode.controller import ModifierPrefix, Settings
from maddenmode.gui.settings_dialog import SettingsDialog
from maddenmode.pen import DEFAULT_PENS, Pen


class FakeBackend:
    def __init__(self, fail: bool = False) -> None:
        self.bindings: dict[str, object] = {}
        self.fail = fail
        self.unregistered = False

    def register(self, bindings: dict) -> None:  # type: ignore[type-arg]
        if self.fail:
            raise OSError("could not register Ctrl+Shift+D (is another app using it?)")
        self.bindings = dict(bindings)

    def unregister_all(self) -> None:
        self.unregistered = True


class FakeDialog:
    def __init__(self, result: QDialog.DialogCode, values: tuple) -> None:  # type: ignore[type-arg]
        self.result = result
        self.values = values

    def exec(self) -> int:
        return (
            int(self.result.value)
            if hasattr(self.result, "value")
            else int(self.result)
        )

    def result_values(self):  # type: ignore[no-untyped-def]
        return self.values


def shutdown(app: MaddenMode) -> None:
    for w in (app.overlay, app.toolbar, app.toast):
        w.close()
    app.tray.hide()


def make(tmp_path: Path, **kwargs):  # type: ignore[no-untyped-def]
    return MaddenMode(
        QApplication.instance(), settings_path=tmp_path / "s.json", **kwargs
    )


def test_builds_with_defaults_when_there_is_no_settings_file(
    qapp: QApplication, tmp_path: Path
) -> None:
    app = make(tmp_path)
    assert app.controller.pens == DEFAULT_PENS
    assert app.load_warning is None
    shutdown(app)


def test_start_shows_overlay_and_toolbar_in_the_given_area(
    qapp: QApplication, tmp_path: Path
) -> None:
    app = make(tmp_path)
    area = QRect(10, 20, 800, 500)
    app.start(geometry=area)
    assert app.overlay.isVisible()
    assert app.overlay.geometry() == area
    assert app.toolbar.isVisible()
    assert app.toolbar.geometry().right() <= area.right()
    shutdown(app)


def test_start_without_an_area_uses_the_screen(
    qapp: QApplication, tmp_path: Path
) -> None:
    app = make(tmp_path)
    app.start()
    assert app.overlay.isVisible()
    assert app.overlay.width() > 0
    shutdown(app)


def test_a_bad_settings_file_is_reported_not_fatal(
    qapp: QApplication, tmp_path: Path
) -> None:
    (tmp_path / "s.json").write_text("{nope")
    app = make(tmp_path)
    assert app.load_warning is not None
    app.start(geometry=QRect(0, 0, 800, 500))
    assert "Could not read" in app.toast.text
    shutdown(app)


def test_loads_saved_settings(qapp: QApplication, tmp_path: Path) -> None:
    settings_store.save(tmp_path / "s.json", Settings(fade_all_s=6.0), (Pen("saved"),))
    app = make(tmp_path)
    assert app.controller.settings.fade_all_s == 6.0
    assert [p.name for p in app.controller.pens] == ["saved"]
    shutdown(app)


def test_accepting_the_dialog_applies_and_saves(
    qapp: QApplication, tmp_path: Path
) -> None:
    new = (Settings(prefix=ModifierPrefix.CTRL_ALT, fade_all_s=2.0), (Pen("new"),))
    app = make(
        tmp_path,
        dialog_factory=lambda s, p: FakeDialog(QDialog.DialogCode.Accepted, new),
    )
    assert app.open_settings() is True
    assert app.controller.settings.prefix == ModifierPrefix.CTRL_ALT
    assert [p.name for p in app.controller.pens] == ["new"]
    saved, pens, warning = settings_store.load(tmp_path / "s.json")
    assert warning is None
    assert saved.fade_all_s == 2.0
    assert [p.name for p in pens] == ["new"]
    shutdown(app)


def test_cancelling_the_dialog_changes_nothing(
    qapp: QApplication, tmp_path: Path
) -> None:
    new = (Settings(fade_all_s=9.0), (Pen("new"),))
    app = make(
        tmp_path,
        dialog_factory=lambda s, p: FakeDialog(QDialog.DialogCode.Rejected, new),
    )
    assert app.open_settings() is False
    assert app.controller.pens == DEFAULT_PENS
    assert not (tmp_path / "s.json").exists()
    shutdown(app)


def test_hotkeys_follow_the_prefix_setting(qapp: QApplication, tmp_path: Path) -> None:
    backend = FakeBackend()
    app = make(tmp_path, hotkeys=backend)
    app.start(geometry=QRect(0, 0, 800, 500))
    assert "Ctrl+Shift+D" in backend.bindings
    app.apply(Settings(prefix=ModifierPrefix.CTRL_ALT), DEFAULT_PENS)
    assert "Ctrl+Alt+D" in backend.bindings
    assert "Ctrl+Shift+D" not in backend.bindings
    shutdown(app)


def test_a_hotkey_clash_is_reported_not_fatal(
    qapp: QApplication, tmp_path: Path
) -> None:
    app = make(tmp_path, hotkeys=FakeBackend(fail=True))
    app.start(geometry=QRect(0, 0, 800, 500))
    assert "another app" in app.toast.text
    shutdown(app)


def test_a_failed_save_is_reported_not_fatal(
    qapp: QApplication, tmp_path: Path
) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x")  # a file where a directory is needed
    app = MaddenMode(QApplication.instance(), settings_path=blocker / "s.json")
    app.apply(Settings(), DEFAULT_PENS)
    assert "Could not save" in app.toast.text
    shutdown(app)


def test_quit_unregisters_hotkeys_and_stops_the_app(
    qapp: QApplication, tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    backend = FakeBackend()
    app = make(tmp_path, hotkeys=backend)
    stopped: list[bool] = []
    monkeypatch.setattr(app.qapp, "quit", lambda: stopped.append(True))
    app.quit()
    assert backend.unregistered
    assert stopped == [True]
    shutdown(app)


def test_quit_works_without_hotkeys(
    qapp: QApplication, tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    app = make(tmp_path)
    stopped: list[bool] = []
    monkeypatch.setattr(app.qapp, "quit", lambda: stopped.append(True))
    app.quit()
    assert stopped == [True]
    shutdown(app)


def test_the_default_dialog_is_the_real_settings_dialog(qapp: QApplication) -> None:
    assert isinstance(_default_dialog(Settings(), DEFAULT_PENS), SettingsDialog)


def test_start_records_no_errors_when_all_is_well(
    qapp: QApplication, tmp_path: Path
) -> None:
    app = make(tmp_path, hotkeys=FakeBackend())
    app.start(geometry=QRect(0, 0, 800, 500))
    assert app.startup_errors == []
    shutdown(app)


def test_start_records_a_bad_settings_file_and_a_hotkey_clash(
    qapp: QApplication, tmp_path: Path
) -> None:
    (tmp_path / "s.json").write_text("{nope")
    app = make(tmp_path, hotkeys=FakeBackend(fail=True))
    app.start(geometry=QRect(0, 0, 800, 500))
    assert len(app.startup_errors) == 2
    assert any("Could not read" in e for e in app.startup_errors)
    assert any("another app" in e for e in app.startup_errors)
    shutdown(app)


def test_smoke_test_passes_on_a_healthy_start(
    qapp: QApplication, tmp_path: Path
) -> None:
    app = make(tmp_path, hotkeys=FakeBackend())
    assert run_smoke_test(app, milliseconds=30) == 0
    shutdown(app)


def test_smoke_test_fails_on_a_bad_settings_file(
    qapp: QApplication, tmp_path: Path, capsys
) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "s.json").write_text("{nope")
    app = make(tmp_path)
    assert run_smoke_test(app, milliseconds=30) == 1
    assert "startup problem" in capsys.readouterr().err
    shutdown(app)


def test_smoke_test_fails_when_hotkeys_cannot_register(
    qapp: QApplication, tmp_path: Path
) -> None:
    app = make(tmp_path, hotkeys=FakeBackend(fail=True))
    assert run_smoke_test(app, milliseconds=30) == 1
    shutdown(app)


def test_smoke_test_fails_if_the_overlay_or_toolbar_disappear(
    qapp: QApplication, tmp_path: Path
) -> None:
    app = make(tmp_path)
    QTimer.singleShot(5, app.overlay.hide)
    QTimer.singleShot(5, app.toolbar.hide)
    assert run_smoke_test(app, milliseconds=60) == 1
    assert "the overlay is not visible" in app.startup_errors
    assert "the toolbar is not visible" in app.startup_errors
    shutdown(app)
