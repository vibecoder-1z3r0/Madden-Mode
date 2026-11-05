#!/usr/bin/env python3
"""Generate the README screenshots from the real widgets and renderer.

    uv run python scripts/screenshots.py [output_dir]      (or `make screenshots`)

Everything is rendered offscreen (no display needed). The "overlay" picture is
a composite: the real overlay, toolbar and toast are grabbed and drawn over a
fake game frame, because a headless run has no real desktop to sit on top of.
"""

import math
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRect  # noqa: E402
from PySide6.QtGui import QColor, QFont, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from maddenmode.app import MaddenMode  # noqa: E402
from maddenmode.gui.render import paint_scene  # noqa: E402
from maddenmode.gui.settings_dialog import SettingsDialog  # noqa: E402
from maddenmode.palette import PALETTE  # noqa: E402
from maddenmode.pen import DissipationMode, Pen  # noqa: E402
from maddenmode.scene import Scene  # noqa: E402

W, H = 1000, 520
GREEN = QColor(34, 94, 52)
STRIPE = QColor(38, 102, 57)


class Clock:
    now = 0.0

    def __call__(self) -> float:
        return self.now


def game_frame(width: int, height: int) -> QImage:
    """A stand-in for a game: a striped field with a few players."""
    frame = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(frame)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.fillRect(0, 0, width, height, GREEN)
    for x in range(0, width, 80):
        p.fillRect(x, 0, 40, height, STRIPE)
    p.setPen(QColor(235, 235, 235, 200))
    for x in (120, 500, 880):
        p.drawLine(x, 0, x, height)
    p.setPen(QColor(0, 0, 0, 0))
    p.setBrush(QColor(40, 90, 200))
    for x, y in [(300, 200), (340, 280), (300, 370), (380, 240)]:
        p.drawEllipse(QPointF(x, y), 13, 13)
    p.setBrush(QColor(200, 50, 50))
    for x, y in [(580, 210), (620, 300), (580, 380), (670, 250)]:
        p.drawEllipse(QPointF(x, y), 13, 13)
    p.end()
    return frame


def caption(image: QImage, text: str) -> None:
    p = QPainter(image)
    font = QFont()
    font.setPointSize(10)
    font.setBold(True)
    p.setFont(font)
    p.setPen(QColor(255, 255, 255))
    p.drawText(QPointF(20, image.height() - 14), text)
    p.end()


def overlay_screenshot(out: Path) -> None:
    clock = Clock()
    settings_path = Path(tempfile.mkdtemp()) / "settings.json"
    qapp = QApplication.instance() or QApplication([])
    app = MaddenMode(qapp, settings_path=settings_path, clock=clock)  # type: ignore[arg-type]
    app.start(geometry=QRect(0, 0, W, H))
    c = app.controller
    c.color_index = None  # the app starts on yellow; show each pen's own color
    c.set_draw_mode(True, 0.0)

    def draw(points: list[tuple[float, float]], t0: float, t1: float, lift: bool):
        n = len(points)
        for i, (x, y) in enumerate(points):
            t = t0 + (t1 - t0) * i / (n - 1)
            (c.pointer_down if i == 0 else c.pointer_move)(x, y, t)
        if lift:
            c.pointer_up(t1)

    now = 3.5
    c.select_pen(0)  # marker
    circle = [
        (
            300 + 42 * math.cos(i / 40 * 2 * math.pi),
            200 + 42 * math.sin(i / 40 * 2 * math.pi),
        )
        for i in range(41)
    ]
    draw(circle, 0.0, 0.8, True)
    draw([(342, 200), (400, 174), (470, 172), (458, 158)], 0.9, 1.3, True)
    draw([(470, 172), (456, 188)], 1.3, 1.4, True)
    c.select_pen(1)  # highlighter
    draw([(150 + i * 6, 320 + 10 * math.sin(i / 9)) for i in range(60)], 1.5, 2.0, True)
    c.select_pen(3)  # comet, still being drawn
    comet = [
        (560 + i * 4.2, 190 + 60 * math.sin(i / 70 * 2 * math.pi) + i * 0.6)
        for i in range(71)
    ]
    draw(comet, 1.8, now, False)
    c.select_color(1)  # red, so the toast describes the pen
    clock.now = now

    frame = game_frame(W, H)
    p = QPainter(frame)
    p.drawImage(0, 0, app.overlay.grab().toImage())
    p.drawImage(app.toolbar.pos(), app.toolbar.grab().toImage())
    p.drawImage(W // 2 - app.toast.width() // 2, 108, app.toast.grab().toImage())
    p.end()
    caption(frame, "Overlay, toolbar and toast (composite over a fake game)")
    frame.save(str(out / "overlay.png"))

    dialog = SettingsDialog(c.settings, c.pens)
    dialog.show()  # at its own default size, as a user sees it
    dialog.grab().save(str(out / "settings.png"))
    dialog.close()

    app.tray.menu.adjustSize()
    app.tray.menu.grab().save(str(out / "tray-menu.png"))
    for widget in (app.overlay, app.toolbar, app.toast):
        widget.close()


def dissipation_screenshot(out: Path) -> None:
    """The three dissipation modes over time, drawn by the real renderer."""
    pens = [
        ("HOLD", Pen("hold", color=PALETTE[3], width=9, feather=2)),
        (
            "TIMED FADE",
            Pen(
                "timed",
                color=PALETTE[3],
                width=9,
                feather=2,
                mode=DissipationMode.TIMED_FADE,
                hold_s=1.0,
                fade_s=2.0,
            ),
        ),
        (
            "TAIL-FIRST FADE",
            Pen(
                "tail",
                color=PALETTE[3],
                width=9,
                feather=2,
                mode=DissipationMode.TAIL_FIRST,
                hold_s=0.0,
                fade_s=1.5,
            ),
        ),
    ]
    times = [0.5, 1.0, 2.0, 3.0]
    pw, ph, left, top = 240, 170, 130, 40
    image = QImage(
        left + pw * len(times),
        top + ph * len(pens),
        QImage.Format.Format_ARGB32_Premultiplied,
    )
    image.fill(QColor(24, 24, 28))
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    font = QFont()
    font.setPointSize(10)
    font.setBold(True)
    p.setFont(font)
    p.setPen(QColor(235, 235, 235))

    n = 60
    points = [
        (20 + i / n * (pw - 40), ph - 35 - 80 * math.sin(i / n * math.pi))
        for i in range(n + 1)
    ]
    for col, now in enumerate(times):
        state = "(drawing)" if now < 1.0 else "(pen up)" if now == 1.0 else ""
        p.drawText(left + col * pw + 40, 26, f"t = {now:.1f} s {state}")
    for row, (label, pen) in enumerate(pens):
        p.drawText(8, top + row * ph + ph // 2, label)
        for col, now in enumerate(times):
            scene = Scene()
            stroke = scene.begin_stroke(pen, *points[0], 0.0)
            for i, (x, y) in enumerate(points[1:], start=1):
                stroke.add_point(x, y, i / n * 1.0)  # drawn over one second
            stroke.lift(1.0)
            cell = game_frame(pw - 4, ph - 4)
            cp = QPainter(cell)
            cp.setRenderHint(QPainter.RenderHint.Antialiasing)
            paint_scene(cp, scene, now)
            cp.end()
            p.drawImage(left + col * pw + 2, top + row * ph + 2, cell)
    p.end()
    image.save(str(out / "dissipation.png"))


def target_screenshot(out: Path) -> None:
    """The "Where to draw" dialog with two monitors and a few example windows."""
    from maddenmode.gui.target_dialog import TargetDialog
    from maddenmode.targeting import MonitorTarget, Rect, ScreenInfo
    from maddenmode.windows import WindowInfo, WindowState

    class SampleWindows:
        available = True

        def list_windows(self) -> list[WindowInfo]:
            return [
                WindowInfo(1, "Match replay - Game", Rect(0, 0, 1600, 900)),
                WindowInfo(2, "Browser", Rect(0, 0, 1280, 800)),
                WindowInfo(3, "Video call", Rect(0, 0, 960, 540)),
            ]

        def get_state(self, handle: int) -> WindowState:
            raise AssertionError("the dialog only lists windows")

    screens = [
        ScreenInfo(0, "Main display", Rect(0, 0, 1920, 1080), 1.0, primary=True),
        ScreenInfo(1, "Second display", Rect(1920, 0, 2560, 1440), 1.0),
    ]
    dialog = TargetDialog(screens, SampleWindows(), MonitorTarget(0))
    dialog.resize(560, 460)
    dialog.show()
    dialog.grab().save(str(out / "target.png"))
    dialog.close()


def icon_screenshot(out: Path) -> None:
    """The icon at tray sizes on a light and a dark taskbar, idle and drawing."""
    from maddenmode.gui.icons import draw_icon

    sizes = [16, 24, 32, 48, 64]
    variants = [
        ("idle", PALETTE[0], False),
        ("idle", PALETTE[1], False),
        ("idle", PALETTE[3], False),
        ("drawing", PALETTE[1], True),
    ]
    cell = 150
    bars = [
        ("light taskbar", QColor(243, 243, 243)),
        ("dark taskbar", QColor(32, 32, 32)),
    ]
    image = QImage(
        cell * len(sizes) + 160,
        len(bars) * len(variants) * 70 + 40,
        QImage.Format.Format_ARGB32_Premultiplied,
    )
    image.fill(QColor(120, 120, 120))
    p = QPainter(image)
    font = QFont()
    font.setPointSize(9)
    p.setFont(font)
    y = 20
    for bar_name, bar in bars:
        for label, color, drawing in variants:
            p.fillRect(0, y, image.width(), 66, bar)
            p.setPen(
                QColor(0, 0, 0) if bar.lightness() > 128 else QColor(255, 255, 255)
            )
            rgb = QColor(*color.rgb)
            p.drawText(8, y + 28, bar_name)
            p.drawText(8, y + 46, f"{label}, {color.name}")
            for i, size in enumerate(sizes):
                p.drawPixmap(
                    170 + i * cell, y + (66 - size) // 2, draw_icon(size, rgb, drawing)
                )
            y += 70
    p.end()
    image.save(str(out / "icon.png"))


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/screenshots")
    out.mkdir(parents=True, exist_ok=True)
    qapp = QApplication.instance() or QApplication([])
    overlay_screenshot(out)
    dissipation_screenshot(out)
    target_screenshot(out)
    icon_screenshot(out)
    print(f"wrote {sorted(p.name for p in out.glob('*.png'))} to {out}")
    qapp.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
