"""Translate Qt key events into the key strings the Controller understands."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

_NAMED = {
    int(Qt.Key.Key_Escape): "Esc",
    int(Qt.Key.Key_BracketLeft): "[",
    int(Qt.Key.Key_BracketRight): "]",
}


def key_string(event: QKeyEvent) -> str | None:
    """'Ctrl+Shift+D', 'Esc', '3', ']' ... or None for keys we don't use."""
    key = int(event.key())
    if key in _NAMED:
        base = _NAMED[key]
    elif int(Qt.Key.Key_A) <= key <= int(Qt.Key.Key_Z):
        base = chr(key)
    elif int(Qt.Key.Key_0) <= key <= int(Qt.Key.Key_9):
        base = chr(key)
    else:
        return None

    mods = event.modifiers()
    parts = []
    if mods & Qt.KeyboardModifier.ControlModifier:
        parts.append("Ctrl")
    if mods & Qt.KeyboardModifier.ShiftModifier:
        parts.append("Shift")
    if mods & Qt.KeyboardModifier.AltModifier:
        parts.append("Alt")
    return "+".join([*parts, base])
