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


# -- choosing where to draw ---------------------------------------------------

from maddenmode.targeting import (  # noqa: E402
    MonitorTarget,
    Rect,
    ScreenInfo,
    WindowTarget,
)
from maddenmode.windows import (  # noqa: E402
    WindowInfo,
    WindowKind,
    WindowState,
)

SCREEN_A = ScreenInfo(0, "Left", Rect(0, 0, 1920, 1080), 1.0, primary=True)
SCREEN_B = ScreenInfo(1, "Right", Rect(1920, 0, 1280, 720), 1.0)
SCREENS = [SCREEN_A, SCREEN_B]


class FakeWindows:
    available = True

    def __init__(self) -> None:
        self.state = WindowState(WindowKind.VISIBLE, Rect(200, 100, 800, 600))

    def list_windows(self) -> list[WindowInfo]:
        return [WindowInfo(77, "Game", Rect(200, 100, 800, 600))]

    def get_state(self, handle: int) -> WindowState:
        return self.state


class FakeTargetDialog:
    def __init__(self, accept: bool, target) -> None:  # type: ignore[no-untyped-def]
        self.accept = accept
        self.target = target

    def exec(self) -> int:
        return 1 if self.accept else 0

    def result_target(self):  # type: ignore[no-untyped-def]
        return self.target


def make_targeted(tmp_path: Path, **kwargs):  # type: ignore[no-untyped-def]
    windows = kwargs.pop("windows", None) or FakeWindows()
    app = MaddenMode(
        QApplication.instance(),
        settings_path=tmp_path / "s.json",
        screens=lambda: SCREENS,
        window_backend=windows,
        **kwargs,
    )
    return app, windows


def area(app: MaddenMode) -> tuple[int, int, int, int]:
    g = app.overlay.geometry()
    return g.x(), g.y(), g.width(), g.height()


def test_by_default_the_overlay_covers_the_first_monitor(
    qapp: QApplication, tmp_path: Path
) -> None:
    app, _ = make_targeted(tmp_path)
    app.start()
    assert area(app) == (0, 0, 1920, 1080)
    shutdown(app)


def test_the_saved_monitor_is_used_at_startup(
    qapp: QApplication, tmp_path: Path
) -> None:
    settings_store.save(tmp_path / "s.json", Settings(monitor=1), DEFAULT_PENS)
    app, _ = make_targeted(tmp_path)
    app.start()
    assert area(app) == (1920, 0, 1280, 720)
    shutdown(app)


def test_an_unplugged_monitor_falls_back_to_the_primary_with_a_message(
    qapp: QApplication, tmp_path: Path
) -> None:
    settings_store.save(tmp_path / "s.json", Settings(monitor=5), DEFAULT_PENS)
    app, _ = make_targeted(tmp_path)
    app.start()
    assert area(app) == (0, 0, 1920, 1080)
    assert "Monitor 6 was not found" in app.toast.text
    shutdown(app)


def test_a_given_area_overrides_the_target(qapp: QApplication, tmp_path: Path) -> None:
    app, _ = make_targeted(tmp_path)
    app.start(geometry=QRect(5, 6, 700, 500))
    assert area(app) == (5, 6, 700, 500)
    shutdown(app)


def test_choosing_a_monitor_moves_the_overlay_and_is_remembered(
    qapp: QApplication, tmp_path: Path
) -> None:
    app, _ = make_targeted(tmp_path)
    app.start()
    app.set_target(MonitorTarget(1))
    assert area(app) == (1920, 0, 1280, 720)
    assert "Drawing over: Monitor 2" in app.toast.text
    assert settings_store.load(tmp_path / "s.json")[0].monitor == 1
    shutdown(app)


def test_the_toolbar_moves_with_the_chosen_monitor(
    qapp: QApplication, tmp_path: Path
) -> None:
    app, _ = make_targeted(tmp_path)
    app.start()
    app.set_target(MonitorTarget(1))
    assert app.toolbar.geometry().right() <= 1920 + 1280
    assert app.toolbar.geometry().x() >= 1920
    shutdown(app)


def test_pinning_a_window_sizes_the_overlay_to_it_and_follows(
    qapp: QApplication, tmp_path: Path
) -> None:
    app, windows = make_targeted(tmp_path)
    app.start()
    app.set_target(WindowTarget(77, "Game"))
    assert area(app) == (200, 100, 800, 600)
    assert app.follower.active
    windows.state = WindowState(WindowKind.VISIBLE, Rect(400, 300, 640, 480))
    app.follower.tick()
    assert area(app) == (400, 300, 640, 480)
    shutdown(app)


def test_a_pinned_window_is_not_saved(qapp: QApplication, tmp_path: Path) -> None:
    app, _ = make_targeted(tmp_path)
    app.start()
    app.set_target(WindowTarget(77, "Game"))
    assert not (tmp_path / "s.json").exists()  # nothing to remember
    assert app.controller.settings.monitor == 0
    shutdown(app)


def test_a_window_that_is_already_gone_falls_back_to_the_monitor(
    qapp: QApplication, tmp_path: Path
) -> None:
    app, windows = make_targeted(tmp_path)
    app.start()
    windows.state = WindowState(WindowKind.GONE)
    app.set_target(WindowTarget(77, "Game"))
    assert app.controller.target == MonitorTarget(0)
    assert area(app) == (0, 0, 1920, 1080)
    assert not app.follower.active
    shutdown(app)


def test_a_pinned_window_that_closes_returns_to_the_monitor(
    qapp: QApplication, tmp_path: Path
) -> None:
    app, windows = make_targeted(tmp_path)
    app.start()
    app.set_target(WindowTarget(77, "Game"))
    windows.state = WindowState(WindowKind.GONE)
    app.follower.tick()
    assert app.controller.target == MonitorTarget(0)
    assert area(app) == (0, 0, 1920, 1080)
    assert "closed" in app.toast.text
    assert "Monitor 1" in app.toast.text
    shutdown(app)


def test_a_closed_window_returns_to_the_saved_monitor_not_the_first(
    qapp: QApplication, tmp_path: Path
) -> None:
    settings_store.save(tmp_path / "s.json", Settings(monitor=1), DEFAULT_PENS)
    app, windows = make_targeted(tmp_path)
    app.start()
    app.set_target(WindowTarget(77, "Game"))
    windows.state = WindowState(WindowKind.GONE)
    app.follower.tick()
    assert area(app) == (1920, 0, 1280, 720)
    shutdown(app)


def test_a_pinned_window_survives_applying_settings(
    qapp: QApplication, tmp_path: Path
) -> None:
    app, _ = make_targeted(tmp_path)
    app.start()
    app.set_target(WindowTarget(77, "Game"))
    app.apply(Settings(fade_all_s=3.0), DEFAULT_PENS)
    assert app.controller.target == WindowTarget(77, "Game")
    shutdown(app)


def test_the_target_dialog_applies_the_choice(
    qapp: QApplication, tmp_path: Path
) -> None:
    app, _ = make_targeted(
        tmp_path,
        target_dialog_factory=lambda s, b, c: FakeTargetDialog(True, MonitorTarget(1)),
    )
    app.start()
    assert app.open_target_dialog() is True
    assert area(app) == (1920, 0, 1280, 720)
    shutdown(app)


def test_cancelling_or_choosing_nothing_changes_nothing(
    qapp: QApplication, tmp_path: Path
) -> None:
    for dialog in (
        FakeTargetDialog(False, MonitorTarget(1)),
        FakeTargetDialog(True, None),
    ):
        app, _ = make_targeted(
            tmp_path, target_dialog_factory=lambda s, b, c, d=dialog: d
        )
        app.start()
        assert app.open_target_dialog() is False
        assert area(app) == (0, 0, 1920, 1080)
        shutdown(app)


def test_the_dialog_is_given_the_screens_windows_and_current_target(
    qapp: QApplication, tmp_path: Path
) -> None:
    seen: list[tuple] = []  # type: ignore[type-arg]

    def factory(screens, backend, current):  # type: ignore[no-untyped-def]
        seen.append((screens, backend, current))
        return FakeTargetDialog(False, None)

    app, windows = make_targeted(tmp_path, target_dialog_factory=factory)
    app.open_target_dialog()
    assert seen == [(SCREENS, windows, MonitorTarget(0))]
    shutdown(app)


def test_quitting_stops_following(
    qapp: QApplication, tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    app, _ = make_targeted(tmp_path)
    app.start()
    app.set_target(WindowTarget(77, "Game"))
    monkeypatch.setattr(app.qapp, "quit", lambda: None)
    app.quit()
    assert not app.follower.active
    shutdown(app)


def test_without_window_support_a_monitor_still_works(
    qapp: QApplication, tmp_path: Path
) -> None:
    from maddenmode.windows import NullWindowBackend

    app, _ = make_targeted(tmp_path, windows=NullWindowBackend())
    app.start()
    app.set_target(MonitorTarget(1))
    assert area(app) == (1920, 0, 1280, 720)
    shutdown(app)


def test_the_default_window_backend_matches_the_platform(
    qapp: QApplication, tmp_path: Path
) -> None:
    import sys

    app = make(tmp_path)
    assert app.window_backend.available == (sys.platform == "win32")
    shutdown(app)


def test_the_default_target_dialog_is_the_real_one(qapp: QApplication) -> None:
    from maddenmode.app import _default_target_dialog
    from maddenmode.gui.target_dialog import TargetDialog
    from maddenmode.windows import NullWindowBackend

    dialog = _default_target_dialog(SCREENS, NullWindowBackend(), MonitorTarget(0))
    assert isinstance(dialog, TargetDialog)


def test_with_no_screens_at_all_it_still_shows_a_default_area(
    qapp: QApplication, tmp_path: Path
) -> None:
    app = MaddenMode(
        QApplication.instance(),
        settings_path=tmp_path / "s.json",
        screens=lambda: [],
        window_backend=FakeWindows(),
    )
    app.start()
    assert area(app) == (0, 0, 1280, 720)
    shutdown(app)
