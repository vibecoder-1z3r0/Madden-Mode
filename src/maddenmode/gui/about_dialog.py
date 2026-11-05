"""The About window: version, links, license, who made it and how."""

import html
import platform
import sys

import PySide6
from PySide6.QtCore import Qt, qVersion
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from maddenmode import about
from maddenmode.gui.icons import draw_icon

ICON_SIZE = 96


def link(url: str, text: str | None = None) -> str:
    return f'<a href="{html.escape(url, quote=True)}">{html.escape(text or url)}</a>'


def running_details() -> str:
    """What is running and on what, for a bug report."""
    return about.details_text(
        python=sys.version.split()[0],
        qt=qVersion(),
        pyside=PySide6.__version__,
        platform=platform.platform(),
    )


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"About {about.APP_NAME}")
        # the overlay and toolbar are always on top; stay above them
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        self.icon_label = QLabel()
        self.icon_label.setPixmap(draw_icon(ICON_SIZE))
        header.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignTop)
        titles = QVBoxLayout()
        self.title_label = QLabel(f"<h2>{html.escape(about.APP_NAME)}</h2>")
        self.version_label = QLabel(about.version_label())
        self.tagline_label = QLabel(about.TAGLINE)
        self.tagline_label.setWordWrap(True)
        titles.addWidget(self.title_label)
        titles.addWidget(self.version_label)
        titles.addWidget(self.tagline_label)
        note = about.stage_note()
        self.stage_label = QLabel(note or "")
        self.stage_label.setWordWrap(True)
        self.stage_label.setVisible(note is not None)
        titles.addWidget(self.stage_label)
        titles.addStretch()
        header.addLayout(titles, 1)
        layout.addLayout(header)

        self.details_label = QLabel(self._details_html())
        self.details_label.setWordWrap(True)
        self.details_label.setTextFormat(Qt.TextFormat.RichText)
        self.details_label.setOpenExternalLinks(True)
        self.details_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.LinksAccessibleByMouse
            | Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.details_label)

        self.license_text = QPlainTextEdit(
            f"{about.LICENSE_NAME}\n{about.COPYRIGHT}\n\n{about.MIT_TERMS}"
        )
        self.license_text.setReadOnly(True)
        self.license_text.setMinimumHeight(120)
        layout.addWidget(self.license_text, 1)

        buttons = QDialogButtonBox()
        self.copy_button = QPushButton("Copy details")
        self.copy_button.setToolTip(
            "Copy the version and platform, to paste into a bug report"
        )
        self.copy_button.clicked.connect(self.copy_details)
        buttons.addButton(self.copy_button, QDialogButtonBox.ButtonRole.ActionRole)
        close = buttons.addButton(QDialogButtonBox.StandardButton.Close)
        close.clicked.connect(self.accept)
        layout.addWidget(buttons)

    def _details_html(self) -> str:
        rows = [
            ("Project", link(about.REPO_URL)),
            ("Vibe-Coder", link(about.OWNER_URL, about.OWNER_NAME)),
            ("AI attribution", link(about.aia_url(), about.AIA_STATEMENT)),
            (
                "License",
                f"{html.escape(about.LICENSE_NAME)}, {html.escape(about.COPYRIGHT)}"
                f" ({link(about.REPO_LICENSE_URL, 'LICENSE')}).<br>"
                f"{html.escape(about.MIT_SUMMARY)}",
            ),
            ("Built with", html.escape(about.NOTICE_QT)),
        ]
        return "".join(
            f'<p style="margin: 0 0 7px 0"><b>{name}:</b> {value}</p>'
            for name, value in rows
        )

    def details_text(self) -> str:
        return running_details()

    def copy_details(self) -> None:
        QGuiApplication.clipboard().setText(self.details_text())
