"""The documented hotkeys must be the ones the code has."""

from pathlib import Path

from maddenmode.controller import DRAW_MODE_KEYS, GLOBAL_KEYS

ROOT = Path(__file__).resolve().parents[2]


def read(name: str) -> str:
    return (ROOT / name).read_text()


def test_the_readme_lists_every_global_hotkey() -> None:
    readme = read("README.md")
    for key in GLOBAL_KEYS:
        assert f"`Ctrl+Shift+{key}`" in readme, f"README is missing Ctrl+Shift+{key}"


def test_the_readme_does_not_list_a_key_that_no_longer_exists() -> None:
    readme = read("README.md")
    listed = {
        line.split("`Ctrl+Shift+")[1][0]
        for line in readme.splitlines()
        if line.startswith("| `Ctrl+Shift+")
    }
    assert listed == set(GLOBAL_KEYS)


def test_the_architecture_notes_list_the_same_global_keys() -> None:
    text = read("ARCHITECTURE.md")
    for key in GLOBAL_KEYS:
        assert f"`Ctrl+Shift+{key}`" in text
    assert "Ctrl+Shift+H" not in text


def test_the_demo_prints_the_keys_the_code_has() -> None:
    demo = read("src/maddenmode/demo.py")
    for key in GLOBAL_KEYS:
        assert f"{key} " in demo or f"+{key} " in demo
    assert "H show/hide" not in demo  # the toolbar key moved to X


def test_the_draw_mode_keys_in_the_readme_exist() -> None:
    readme = read("README.md")
    for key in DRAW_MODE_KEYS:
        shown = "`Esc`" if key == "Esc" else f"`{key}`"
        assert shown in readme
