import pytest
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from maddenmode.gui.render import _feather_rings, paint_scene, render_stroke
from maddenmode.palette import PALETTE
from maddenmode.pen import DissipationMode, Pen
from maddenmode.scene import Scene

W, H = 200, 100


def canvas() -> QImage:
    img = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)  # fully transparent
    return img


def paint(scene: Scene, now: float) -> QImage:
    img = canvas()
    p = QPainter(img)
    paint_scene(p, scene, now)
    p.end()
    return img


def line_scene(pen: Pen, lift: bool = True) -> Scene:
    scene = Scene()
    stroke = scene.begin_stroke(pen, 20, 50, 0.0)
    stroke.add_point(100, 50, 0.5)
    stroke.add_point(180, 50, 1.0)
    if lift:
        stroke.lift(1.0)
    return scene


def alpha(img: QImage, x: int, y: int) -> int:
    return img.pixelColor(x, y).alpha()


def test_feather_rings_keep_total_width(qapp: QApplication) -> None:
    for width, feather in [(12.0, 0.0), (12.0, 2.0), (16.0, 2.0), (14.0, 5.0)]:
        rings = _feather_rings(width, feather)
        assert rings[0][0] == pytest.approx(width)  # outermost = total width
        assert rings[-1][1] == 1.0  # core is fully opaque
        alphas = [a for _, a in rings]
        assert alphas == sorted(alphas)  # more opaque towards the middle


def test_empty_canvas_stays_transparent(qapp: QApplication) -> None:
    img = paint(Scene(), 0.0)
    assert alpha(img, 100, 50) == 0


def test_hard_pen_is_opaque_in_the_pen_color(qapp: QApplication) -> None:
    pen = Pen("hard", color=PALETTE[1], width=10, feather=0)
    img = paint(line_scene(pen), 1.0)
    c = img.pixelColor(100, 50)
    assert c.alpha() == 255
    assert (c.red(), c.green(), c.blue()) == PALETTE[1].rgb
    assert alpha(img, 100, 30) == 0  # well off the line
    assert alpha(img, 5, 50) == 0  # before the start


def test_line_has_the_pen_width(qapp: QApplication) -> None:
    pen = Pen("hard", width=10, feather=0)
    img = paint(line_scene(pen), 1.0)
    opaque = [y for y in range(H) if alpha(img, 100, y) == 255]
    assert 9 <= len(opaque) <= 11


def test_feather_fades_the_edge_but_keeps_the_core(qapp: QApplication) -> None:
    pen = Pen("soft", width=16, feather=4)
    img = paint(line_scene(pen), 1.0)
    column = [alpha(img, 100, y) for y in range(40, 61)]
    assert alpha(img, 100, 50) == 255
    assert max(column) == 255
    edge = [a for a in column if 0 < a < 255]
    assert edge, "expected partly transparent edge pixels"
    # alpha falls off monotonically moving away from the centre
    below = [alpha(img, 100, y) for y in range(50, 61)]
    assert below == sorted(below, reverse=True)


def test_feather_does_not_change_total_width(qapp: QApplication) -> None:
    def extent(feather: float) -> int:
        img = paint(line_scene(Pen("p", width=16, feather=feather)), 1.0)
        return sum(1 for y in range(H) if alpha(img, 100, y) > 0)

    assert abs(extent(0) - extent(4)) <= 2


def test_timed_fade_scales_the_whole_stroke(qapp: QApplication) -> None:
    pen = Pen(
        "t", width=10, feather=0, mode=DissipationMode.TIMED_FADE, hold_s=0, fade_s=2
    )
    scene = line_scene(pen)  # pen lifts at t=1.0
    assert alpha(paint(scene, 1.0), 100, 50) == 255
    assert alpha(paint(scene, 2.0), 100, 50) == pytest.approx(128, abs=2)
    assert alpha(paint(scene, 2.0), 30, 50) == pytest.approx(128, abs=2)
    assert alpha(paint(scene, 3.0), 100, 50) == 0


def test_tail_first_fades_the_start_before_the_end(qapp: QApplication) -> None:
    pen = Pen(
        "c", width=10, feather=0, mode=DissipationMode.TAIL_FIRST, hold_s=0, fade_s=2
    )
    img = paint(line_scene(pen, lift=False), 1.0)
    start, middle, end = alpha(img, 30, 50), alpha(img, 100, 50), alpha(img, 170, 50)
    assert start < middle < end  # strictly increasing, even inside one segment
    assert end > 240  # near the newest point, which is still solid
    assert 0 < start < 160  # the oldest part is partly faded


def test_tail_first_keeps_edges_when_masked(qapp: QApplication) -> None:
    pen = Pen(
        "c", width=10, feather=0, mode=DissipationMode.TAIL_FIRST, hold_s=0, fade_s=2
    )
    img = paint(line_scene(pen, lift=False), 1.0)
    # the mask must not eat the stroke's sides: full height at the newest end
    opaque = [y for y in range(H) if alpha(img, 175, y) >= 250]
    assert len(opaque) >= 9


def test_single_point_is_a_dot(qapp: QApplication) -> None:
    scene = Scene()
    scene.begin_stroke(Pen("p", width=12, feather=0), 100, 50, 0.0)
    img = paint(scene, 0.0)
    assert alpha(img, 100, 50) == 255
    assert alpha(img, 100, 40) == 0


def test_fully_faded_stroke_draws_nothing(qapp: QApplication) -> None:
    pen = Pen("t", mode=DissipationMode.TIMED_FADE, hold_s=0, fade_s=1)
    scene = line_scene(pen)
    assert render_stroke(scene.strokes[0], 5.0) is None
    assert alpha(paint(scene, 5.0), 100, 50) == 0


def test_fade_all_applies_to_a_held_stroke(qapp: QApplication) -> None:
    scene = line_scene(Pen("h", width=10, feather=0))
    scene.fade_all(now=2.0, fade_s=2.0)
    assert alpha(paint(scene, 2.0), 100, 50) == 255
    assert alpha(paint(scene, 3.0), 100, 50) == pytest.approx(128, abs=2)
    assert alpha(paint(scene, 4.0), 100, 50) == 0


def test_stroke_with_no_points_renders_nothing(qapp: QApplication) -> None:
    from maddenmode.stroke import Stroke

    assert render_stroke(Stroke(Pen("p")), 0.0) is None
