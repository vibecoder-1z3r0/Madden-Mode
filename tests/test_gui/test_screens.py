from PySide6.QtWidgets import QApplication

from maddenmode.gui.screens import list_screens, to_qrect
from maddenmode.targeting import Rect


def test_lists_at_least_one_screen_with_the_primary_first(qapp: QApplication) -> None:
    screens = list_screens()
    assert len(screens) >= 1
    assert screens[0].primary
    assert [s.index for s in screens] == list(range(len(screens)))
    assert not any(s.primary for s in screens[1:])


def test_screens_have_a_real_size_and_scale(qapp: QApplication) -> None:
    for screen in list_screens():
        assert screen.geometry.width > 0
        assert screen.geometry.height > 0
        assert screen.dpr > 0
        assert screen.name


def test_rect_converts_to_qrect(qapp: QApplication) -> None:
    q = to_qrect(Rect(10, 20, 300, 400))
    assert (q.x(), q.y(), q.width(), q.height()) == (10, 20, 300, 400)
