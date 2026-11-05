"""Translate Qt key events into the key strings the Controller understands.

The key names are the physical keys on every platform: Ctrl is the Control
key, Alt is Alt (Option on a Mac), and Cmd is the Command key on a Mac.

macOS needs care: Qt swaps two of them there. The Command key is reported as
Qt's "Control" modifier, and the Control key is reported as Qt's "Meta"
modifier. Without allowing for that, a real Control+Shift+D press on a Mac
would not match "Ctrl+Shift+D" and Command+Shift+D would match it by mistake.
"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

_NAMED = {
    int(Qt.Key.Key_Escape): "Esc",
    int(Qt.Key.Key_BracketLeft): "[",
    int(Qt.Key.Key_BracketRight): "]",
}


def key_string(event: QKeyEvent, platform: str = sys.platform) -> str | None:
    """'Ctrl+Shift+D', 'Esc', '3', ']' ... or None for keys we don't use.

    A Command press on a Mac is written 'Cmd+...', which no hotkey uses, so it
    can never trigger one by accident (and never clashes with Mac shortcuts).
    """
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
    if platform == "darwin":
        # Qt's swap: its Meta is the Control key and its Control is Command
        control = Qt.KeyboardModifier.MetaModifier
        command: Qt.KeyboardModifier | None = Qt.KeyboardModifier.ControlModifier
    else:
        control = Qt.KeyboardModifier.ControlModifier
        command = None  # the Windows key (Qt's Meta) is not used for hotkeys

    parts = []
    if command is not None and mods & command:
        parts.append("Cmd")
    if mods & control:
        parts.append("Ctrl")
    if mods & Qt.KeyboardModifier.ShiftModifier:
        parts.append("Shift")
    if mods & Qt.KeyboardModifier.AltModifier:
        parts.append("Alt")
    return "+".join([*parts, base])
