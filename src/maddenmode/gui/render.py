"""Draw a Scene to pixels.

Each stroke is drawn as ONE shape into its own transparent layer, using the
Source composition mode so overlapping pieces replace instead of stacking
(stacking caused bright spots and dents in earlier mock-ups). Opacity is then
applied afterwards:

- uniform opacity (hold, timed fade, fade all): the whole layer is drawn at
  that opacity;
- varying opacity (tail-first fade): a second layer holding per-segment
  opacity is multiplied in with DestinationIn.
"""

import math

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)

from maddenmode.dissipation import point_opacity
from maddenmode.scene import Scene
from maddenmode.stroke import Point, Stroke

_UNIFORM_TOLERANCE = 1e-3
_PAD = 4.0  # extra pixels around a stroke's bounds


def _feather_rings(width: float, feather: float) -> list[tuple[float, float]]:
    """(ring width, alpha 0..1) from the outermost ring down to the core.

    The core is solid and the feather is added on each side of it, so the
    total width stays `width` as the feather changes. feather = 0 is just
    the hard core.
    """
    core = max(width - 2.0 * feather, 1.0)
    rings: list[tuple[float, float]] = []
    if feather > 0:
        steps = math.ceil(feather)
        for j in range(steps, 0, -1):
            rings.append((core + 2.0 * j * (feather / steps), 1.0 - j / (steps + 1)))
    rings.append((core, 1.0))
    return rings


def _path(points: list[Point]) -> QPainterPath:
    path = QPainterPath(QPointF(points[0].x, points[0].y))
    for p in points[1:]:
        path.lineTo(QPointF(p.x, p.y))
    return path


def _round_pen(color: QColor, width: float) -> QPen:
    return QPen(
        color,
        width,
        Qt.PenStyle.SolidLine,
        Qt.PenCapStyle.RoundCap,
        Qt.PenJoinStyle.RoundJoin,
    )


def _draw_shape(q: QPainter, stroke: Stroke) -> None:
    pen = stroke.pen
    r, g, b = pen.color.rgb
    points = stroke.points
    q.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
    for ring_width, alpha in _feather_rings(pen.width, pen.feather):
        color = QColor(r, g, b, round(alpha * 255))
        if len(points) == 1:  # a dot: a path with one point draws nothing
            q.setPen(Qt.PenStyle.NoPen)
            q.setBrush(color)
            centre = QPointF(points[0].x, points[0].y)
            q.drawEllipse(centre, ring_width / 2, ring_width / 2)
        else:
            q.setBrush(Qt.BrushStyle.NoBrush)
            q.setPen(_round_pen(color, ring_width))
            q.drawPath(_path(points))


def _apply_varying_opacity(
    q: QPainter, stroke: Stroke, opacities: list[float], bounds: QRect
) -> None:
    """Multiply the layer being painted by a per-segment opacity layer.

    `q` is already translated so scene coordinates draw correctly.
    """
    mask = QImage(bounds.size(), QImage.Format.Format_ARGB32_Premultiplied)
    mask.fill(Qt.GlobalColor.transparent)
    m = QPainter(mask)
    m.setRenderHint(QPainter.RenderHint.Antialiasing)
    m.translate(-bounds.x(), -bounds.y())
    m.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
    # Wider than the stroke so the mask never cuts the shape's own edge.
    width = stroke.pen.width + 2 * _PAD
    pts = stroke.points
    for i in range(len(pts) - 1):
        a = QPointF(pts[i].x, pts[i].y)
        b = QPointF(pts[i + 1].x, pts[i + 1].y)
        # Opacity is interpolated along the segment, so the fade is smooth
        # even with sparse points and neighbouring segments meet seamlessly.
        gradient = QLinearGradient(a, b)
        gradient.setColorAt(0.0, QColor(0, 0, 0, round(opacities[i] * 255)))
        gradient.setColorAt(1.0, QColor(0, 0, 0, round(opacities[i + 1] * 255)))
        m.setPen(
            QPen(
                QBrush(gradient),
                width,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        m.drawLine(a, b)
    m.end()
    q.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    q.drawImage(bounds.topLeft(), mask)


def render_stroke(stroke: Stroke, now: float) -> tuple[QImage, QPoint, float] | None:
    """Render one stroke into a tight layer.

    Returns (layer, top-left in scene coordinates, uniform opacity to draw the
    layer at), or None when nothing of the stroke is visible.
    """
    if not stroke.points:
        return None
    opacities = [point_opacity(stroke, i, now) for i in range(len(stroke.points))]
    if max(opacities) <= 0.0:
        return None

    pen = stroke.pen
    xs = [p.x for p in stroke.points]
    ys = [p.y for p in stroke.points]
    margin = pen.width / 2 + pen.feather + _PAD
    bounds = QRectF(
        min(xs) - margin,
        min(ys) - margin,
        max(xs) - min(xs) + 2 * margin,
        max(ys) - min(ys) + 2 * margin,
    ).toAlignedRect()

    layer = QImage(bounds.size(), QImage.Format.Format_ARGB32_Premultiplied)
    layer.fill(Qt.GlobalColor.transparent)
    q = QPainter(layer)
    q.setRenderHint(QPainter.RenderHint.Antialiasing)
    q.translate(-bounds.x(), -bounds.y())
    _draw_shape(q, stroke)

    if max(opacities) - min(opacities) <= _UNIFORM_TOLERANCE:
        opacity = opacities[0]
    else:
        opacity = 1.0
        _apply_varying_opacity(q, stroke, opacities, bounds)
    q.end()
    return layer, bounds.topLeft(), opacity


def paint_scene(painter: QPainter, scene: Scene, now: float) -> None:
    """Paint every visible stroke onto `painter`, oldest first."""
    painter.save()
    for stroke in scene.strokes:
        rendered = render_stroke(stroke, now)
        if rendered is None:
            continue
        layer, top_left, opacity = rendered
        painter.setOpacity(opacity)
        painter.drawImage(top_left, layer)
    painter.restore()
