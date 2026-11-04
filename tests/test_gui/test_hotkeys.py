import pytest
from PySide6.QtWidgets import QApplication

from maddenmode.controller import Controller, ModifierPrefix, Settings
from maddenmode.gui.hotkeys import (
    MOD_ALT,
    MOD_CONTROL,
    MOD_NOREPEAT,
    MOD_SHIFT,
    WindowsHotkeys,
    bind_controller,
    parse_chord,
)
from maddenmode.scene import Scene


def test_parse_ctrl_shift_letter() -> None:
    flags, vk = parse_chord("Ctrl+Shift+D")
    assert flags == MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT
    assert vk == ord("D")


def test_parse_ctrl_alt_letter() -> None:
    flags, vk = parse_chord("Ctrl+Alt+C")
    assert flags == MOD_CONTROL | MOD_ALT | MOD_NOREPEAT
    assert vk == ord("C")


def test_parse_is_case_insensitive_for_modifiers_and_keys() -> None:
    assert parse_chord("ctrl+shift+f") == parse_chord("Ctrl+Shift+F")


def test_parse_function_keys_and_esc() -> None:
    assert parse_chord("Ctrl+F1")[1] == 0x70
    assert parse_chord("Ctrl+F12")[1] == 0x7B
    assert parse_chord("Ctrl+Esc")[1] == 0x1B


@pytest.mark.parametrize("bad", ["D", "Ctrl+", "Hyper+D", "Ctrl+F25", "Ctrl+Space"])
def test_parse_rejects_bad_chords(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_chord(bad)


class FakeBackend:
    def __init__(self) -> None:
        self.bindings: dict[str, object] = {}

    def register(self, bindings: dict) -> None:  # type: ignore[type-arg]
        self.bindings = dict(bindings)

    def unregister_all(self) -> None:
        self.bindings = {}


def test_bind_controller_registers_the_three_global_chords() -> None:
    backend = FakeBackend()
    bind_controller(backend, Controller(Scene()), lambda: 0.0)
    assert set(backend.bindings) == {"Ctrl+Shift+D", "Ctrl+Shift+C", "Ctrl+Shift+F"}


def test_bind_controller_follows_the_prefix_setting() -> None:
    backend = FakeBackend()
    controller = Controller(Scene(), settings=Settings(prefix=ModifierPrefix.CTRL_ALT))
    bind_controller(backend, controller, lambda: 0.0)
    assert set(backend.bindings) == {"Ctrl+Alt+D", "Ctrl+Alt+C", "Ctrl+Alt+F"}


def test_triggering_a_binding_runs_the_controller_action() -> None:
    backend = FakeBackend()
    controller = Controller(Scene())
    bind_controller(backend, controller, lambda: 5.0)
    backend.bindings["Ctrl+Shift+D"]()  # type: ignore[operator]
    assert controller.draw_mode


def test_windows_backend_refuses_other_platforms(qapp: QApplication) -> None:
    import sys

    if sys.platform == "win32":
        pytest.skip("this checks the non-Windows refusal")
    with pytest.raises(OSError):
        WindowsHotkeys().register({"Ctrl+Shift+D": lambda: None})
