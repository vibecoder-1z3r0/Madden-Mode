import pytest

from maddenmode.targeting import Rect
from maddenmode.windows import (
    NullWindowBackend,
    WindowKind,
    WindowState,
    is_pickable,
)

BIG = Rect(0, 0, 800, 600)


def pickable(**overrides: object) -> bool:
    args: dict[str, object] = {
        "title": "A game",
        "visible": True,
        "minimized": False,
        "cloaked": False,
        "tool_window": False,
        "own_process": False,
        "rect": BIG,
    }
    args.update(overrides)
    return is_pickable(**args)  # type: ignore[arg-type]


def test_an_ordinary_window_is_pickable() -> None:
    assert pickable()


@pytest.mark.parametrize(
    "override",
    [
        {"title": ""},
        {"title": "   "},
        {"visible": False},
        {"minimized": True},
        {"cloaked": True},
        {"tool_window": True},
        {"own_process": True},
        {"rect": Rect(0, 0, 49, 600)},
        {"rect": Rect(0, 0, 800, 49)},
    ],
)
def test_windows_a_person_would_not_pick_are_excluded(override: dict) -> None:  # type: ignore[type-arg]
    assert not pickable(**override)


def test_the_size_limit_is_inclusive() -> None:
    assert pickable(rect=Rect(0, 0, 50, 50))


def test_null_backend_reports_unavailable_and_empty() -> None:
    backend = NullWindowBackend()
    assert not backend.available
    assert backend.list_windows() == []
    assert backend.get_state(123) == WindowState(WindowKind.GONE)
