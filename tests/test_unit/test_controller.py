import pytest

from maddenmode.controller import (
    Controller,
    ModifierPrefix,
    Settings,
    global_bindings,
    normalize_key,
)
from maddenmode.palette import PALETTE
from maddenmode.pen import DEFAULT_PENS, Pen
from maddenmode.scene import Scene
from maddenmode.targeting import MonitorTarget, WindowTarget

TOGGLE = "Ctrl+Shift+D"
CLEAR = "Ctrl+Shift+C"
FADE = "Ctrl+Shift+F"


def make(settings: Settings | None = None) -> Controller:
    return Controller(Scene(), settings=settings)


def test_global_bindings_use_the_prefix() -> None:
    assert set(global_bindings(ModifierPrefix.CTRL_SHIFT)) == {
        "Ctrl+Shift+D",
        "Ctrl+Shift+C",
        "Ctrl+Shift+F",
        "Ctrl+Shift+X",
    }
    assert set(global_bindings(ModifierPrefix.CTRL_ALT)) == {
        "Ctrl+Alt+D",
        "Ctrl+Alt+C",
        "Ctrl+Alt+F",
        "Ctrl+Alt+X",
    }


def test_normalize_key() -> None:
    assert normalize_key("ctrl+shift+d") == "Ctrl+Shift+D"
    assert normalize_key("esc") == "Esc"
    assert normalize_key("]") == "]"


def test_toggle_draw_mode() -> None:
    c = make()
    assert not c.draw_mode
    assert c.press(TOGGLE, 0.0)
    assert c.draw_mode
    assert c.press(TOGGLE, 1.0)
    assert not c.draw_mode


def test_switching_prefix_moves_the_global_keys() -> None:
    c = make(Settings(prefix=ModifierPrefix.CTRL_ALT))
    assert not c.press(TOGGLE, 0.0)  # old prefix now belongs to the game
    assert not c.draw_mode
    assert c.press("Ctrl+Alt+D", 0.0)
    assert c.draw_mode


def test_plain_keys_pass_through_when_not_drawing() -> None:
    c = make()
    for key in ("1", "]", "[", "Esc", "a"):
        assert not c.press(key, 0.0)
    assert c.color_index is None
    assert c.pen_index == 0


def test_number_keys_pick_colors_in_draw_mode() -> None:
    c = make()
    c.press(TOGGLE, 0.0)
    assert c.press("3", 0.0)
    assert c.current_pen.color == PALETTE[2]
    assert c.press("8", 0.0)
    assert c.current_pen.color == PALETTE[7]
    assert not c.press("9", 0.0)  # only 8 colors


def test_pen_cycling_wraps_in_draw_mode() -> None:
    c = make()
    c.press(TOGGLE, 0.0)
    c.press("]", 0.0)
    assert c.current_pen.name == DEFAULT_PENS[1].name
    c.press("[", 0.0)
    c.press("[", 0.0)
    assert c.current_pen.name == DEFAULT_PENS[-1].name


def test_picked_color_carries_across_pens() -> None:
    c = make()
    c.press(TOGGLE, 0.0)
    c.press("5", 0.0)
    c.press("]", 0.0)
    assert c.current_pen.color == PALETTE[4]


def test_esc_exits_draw_mode() -> None:
    c = make()
    c.press(TOGGLE, 0.0)
    assert c.press("Esc", 1.0)
    assert not c.draw_mode


def test_pointer_is_ignored_outside_draw_mode() -> None:
    c = make()
    assert not c.pointer_down(1, 1, 0.0)
    assert c.scene.strokes == []


def test_drawing_a_stroke() -> None:
    c = make()
    c.press(TOGGLE, 0.0)
    assert c.pointer_down(1, 1, 1.0)
    c.pointer_move(2, 2, 1.1)
    c.pointer_move(3, 3, 1.2)
    c.pointer_up(1.3)
    (stroke,) = c.scene.strokes
    assert [(p.x, p.y) for p in stroke.points] == [(1, 1), (2, 2), (3, 3)]
    assert stroke.pen_up_at == 1.3
    c.pointer_move(9, 9, 2.0)  # no active stroke: ignored
    assert len(stroke.points) == 3


def test_leaving_draw_mode_lifts_the_active_stroke() -> None:
    c = make()
    c.press(TOGGLE, 0.0)
    c.pointer_down(0, 0, 1.0)
    c.press(TOGGLE, 2.0)
    (stroke,) = c.scene.strokes
    assert stroke.pen_up_at == 2.0
    assert c.active_stroke is None


def test_clear_all_works_outside_draw_mode() -> None:
    c = make()
    c.press(TOGGLE, 0.0)
    c.pointer_down(0, 0, 0.0)
    c.pointer_up(0.1)
    c.press(TOGGLE, 0.2)
    assert c.press(CLEAR, 0.3)
    assert c.scene.strokes == []


def test_clear_all_drops_the_stroke_being_drawn() -> None:
    c = make()
    c.press(TOGGLE, 0.0)
    c.pointer_down(0, 0, 0.0)
    c.press(CLEAR, 0.1)
    c.pointer_move(5, 5, 0.2)
    assert c.scene.strokes == []


def test_fade_all_uses_the_global_time() -> None:
    c = make(Settings(fade_all_s=3.0))
    c.press(TOGGLE, 0.0)
    c.pointer_down(0, 0, 0.0)
    c.pointer_up(0.1)
    c.press(FADE, 5.0)
    (stroke,) = c.scene.strokes
    assert stroke.cleared_at == 5.0
    assert stroke.clear_fade_s == 3.0


def test_settings_validate_fade_all_time() -> None:
    with pytest.raises(ValueError):
        Settings(fade_all_s=11.0)


def test_hold_to_draw_follows_the_key() -> None:
    c = make(Settings(hold_to_draw=True))
    assert c.press(TOGGLE, 0.0)
    assert c.draw_mode
    c.pointer_down(0, 0, 0.5)
    assert c.release(TOGGLE, 1.0)
    assert not c.draw_mode
    assert c.scene.strokes[0].pen_up_at == 1.0


def test_hold_to_draw_ignores_release_of_other_keys() -> None:
    c = make(Settings(hold_to_draw=True))
    c.press(TOGGLE, 0.0)
    assert not c.release(CLEAR, 0.5)
    assert not c.release("a", 0.5)
    assert c.draw_mode


def test_release_is_ignored_in_toggle_mode() -> None:
    c = make()
    c.press(TOGGLE, 0.0)
    assert not c.release(TOGGLE, 0.1)
    assert c.draw_mode


def test_draw_mode_callback_fires_only_on_change() -> None:
    c = make()
    seen: list[bool] = []
    c.on_draw_mode_changed = seen.append
    c.press(TOGGLE, 0.0)  # on
    c.press("Esc", 1.0)  # off
    c.press("Esc", 2.0)  # already off: no call
    assert seen == [True, False]


def test_controller_needs_a_pen() -> None:
    with pytest.raises(ValueError):
        Controller(Scene(), pens=())


def test_custom_pens() -> None:
    pen = Pen("only")
    c = Controller(Scene(), pens=(pen,))
    c.press(TOGGLE, 0.0)
    c.press("]", 0.0)
    assert c.current_pen.name == "only"


def test_toolbar_toggle_key_is_global() -> None:
    c = make()
    assert c.toolbar_visible
    assert c.press("Ctrl+Shift+X", 0.0)
    assert not c.toolbar_visible
    assert c.press("Ctrl+Shift+X", 0.0)
    assert c.toolbar_visible


def test_listeners_hear_about_every_state_change() -> None:
    c = make()
    calls: list[int] = []
    c.add_listener(lambda: calls.append(1))
    c.toggle_draw(0.0)  # draw mode
    c.select_color(2)
    c.select_pen(1)
    c.next_pen()
    c.prev_pen()
    c.toggle_toolbar()
    assert len(calls) == 6


def test_actions_without_ui_state_do_not_notify() -> None:
    c = make()
    calls: list[int] = []
    c.add_listener(lambda: calls.append(1))
    c.clear_all()
    c.fade_all(0.0)
    assert calls == []


def test_select_color_and_pen_validate_their_index() -> None:
    c = make()
    with pytest.raises(ValueError):
        c.select_color(8)
    with pytest.raises(ValueError):
        c.select_color(-1)
    with pytest.raises(ValueError):
        c.select_pen(len(c.pens))


def test_set_draw_mode_directly() -> None:
    c = make()
    c.set_draw_mode(True, 0.0)
    assert c.draw_mode
    c.set_draw_mode(False, 1.0)
    assert not c.draw_mode


def test_apply_settings_replaces_settings_and_pens() -> None:
    c = make()
    c.select_pen(len(c.pens) - 1)
    calls: list[int] = []
    c.add_listener(lambda: calls.append(1))
    only = (Pen("only"),)
    c.apply_settings(Settings(prefix=ModifierPrefix.CTRL_ALT, fade_all_s=4.0), only)
    assert c.pens == only
    assert c.pen_index == 0  # clamped into range
    assert c.settings.fade_all_s == 4.0
    assert c.press("Ctrl+Alt+D", 0.0)  # new prefix is live
    assert len(calls) >= 2


def test_apply_settings_needs_a_pen() -> None:
    with pytest.raises(ValueError):
        make().apply_settings(Settings(), ())


def test_target_defaults_to_the_saved_monitor() -> None:
    assert make().target == MonitorTarget(0)
    assert make(Settings(monitor=2)).target == MonitorTarget(2)


def test_set_target_notifies_listeners() -> None:
    c = make()
    calls: list[int] = []
    c.add_listener(lambda: calls.append(1))
    c.set_target(WindowTarget(42, "Game"))
    assert c.target == WindowTarget(42, "Game")
    assert calls == [1]


def test_negative_monitor_is_rejected() -> None:
    with pytest.raises(ValueError):
        Settings(monitor=-1)


def test_applying_settings_moves_a_monitor_target() -> None:
    c = make()
    c.apply_settings(Settings(monitor=3), c.pens)
    assert c.target == MonitorTarget(3)


def test_applying_settings_leaves_a_pinned_window_alone() -> None:
    c = make()
    c.set_target(WindowTarget(7, "Game"))
    c.apply_settings(Settings(monitor=3), c.pens)
    assert c.target == WindowTarget(7, "Game")


def test_the_old_toolbar_key_no_longer_does_anything() -> None:
    c = make()
    assert not c.press("Ctrl+Shift+H", 0.0)  # moved to X; H is free for the game
    assert c.toolbar_visible


def test_every_global_hotkey_is_on_the_left_hand_side_of_the_keyboard() -> None:
    # one hand on the keys, the other on the mouse or stylus
    from maddenmode.controller import GLOBAL_KEYS

    assert set(GLOBAL_KEYS) == {"D", "C", "F", "X"}
    assert all(key in "QWERTASDFGZXCVB" for key in GLOBAL_KEYS)


def test_select_pen_by_name() -> None:
    c = make()
    assert c.select_pen_by_name("comet")
    assert c.current_pen.name == "comet"
    assert c.pen_index == next(i for i, p in enumerate(c.pens) if p.name == "comet")


def test_selecting_an_unknown_pen_changes_nothing_and_says_so() -> None:
    c = make()
    c.select_pen(1)
    calls: list[int] = []
    c.add_listener(lambda: calls.append(1))
    assert not c.select_pen_by_name("no such pen")
    assert c.pen_index == 1
    assert calls == []


def test_selecting_a_pen_by_name_notifies_listeners() -> None:
    c = make()
    calls: list[int] = []
    c.add_listener(lambda: calls.append(1))
    c.select_pen_by_name("flash")
    assert calls == [1]


def test_the_controller_itself_still_starts_on_the_first_pen_with_its_own_color() -> (
    None
):
    # the comet-in-yellow start belongs to the app, not to the controller
    c = make()
    assert c.pen_index == 0
    assert c.color_index is None
