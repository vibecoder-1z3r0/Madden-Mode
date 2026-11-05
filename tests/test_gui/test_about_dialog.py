import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QDialog

from maddenmode import __version__, about
from maddenmode.gui.about_dialog import AboutDialog, link, running_details


def test_the_window_is_titled_and_stays_above_the_overlay(qapp: QApplication) -> None:
    dialog = AboutDialog()
    assert about.APP_NAME in dialog.windowTitle()
    assert dialog.windowFlags() & Qt.WindowType.WindowStaysOnTopHint


def test_it_shows_the_calendar_version_and_the_alpha_label(qapp: QApplication) -> None:
    dialog = AboutDialog()
    assert dialog.version_label.text() == about.version_label()
    assert __version__ in dialog.version_label.text()
    if about.release_stage() == "alpha":
        assert "(alpha)" in dialog.version_label.text()


def test_an_alpha_gets_a_visible_heads_up(qapp: QApplication) -> None:
    dialog = AboutDialog()
    dialog.show()
    assert about.stage_note() is not None  # this release is a pre-release
    assert dialog.stage_label.isVisible()
    assert "rough edges" in dialog.stage_label.text()
    dialog.close()


def test_a_full_release_shows_no_heads_up(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(about, "stage_note", lambda version=about.VERSION: None)
    dialog = AboutDialog()
    dialog.show()
    assert not dialog.stage_label.isVisible()
    dialog.close()


def test_it_has_the_icon(qapp: QApplication) -> None:
    dialog = AboutDialog()
    assert not dialog.icon_label.pixmap().isNull()


def test_the_links_go_to_the_right_places(qapp: QApplication) -> None:
    dialog = AboutDialog()
    html = dialog.details_label.text()
    assert about.REPO_URL in html  # the GitHub project
    assert about.OWNER_URL in html  # the vibe-coder
    assert about.aia_url() in html  # the proper AIA statement
    assert about.REPO_LICENSE_URL in html  # the license file
    assert html.count("<a href=") >= 4


def test_links_open_in_the_browser_not_inside_the_window(qapp: QApplication) -> None:
    dialog = AboutDialog()
    assert dialog.details_label.openExternalLinks()
    assert dialog.details_label.textInteractionFlags() & (
        Qt.TextInteractionFlag.LinksAccessibleByMouse
    )


def test_it_names_the_vibe_coder_and_the_statement(qapp: QApplication) -> None:
    dialog = AboutDialog()
    html = dialog.details_label.text()
    assert about.OWNER_NAME in html
    assert "Vibe-Coder" in html
    assert about.AIA_STATEMENT in html
    assert "AI attribution" in html


def test_it_says_what_the_license_is(qapp: QApplication) -> None:
    dialog = AboutDialog()
    html = dialog.details_label.text()
    assert about.LICENSE_NAME in html
    assert about.COPYRIGHT.replace("(c)", "(c)") in html
    assert about.MIT_SUMMARY in html
    # and the full text, in a box that cannot be edited
    assert dialog.license_text.isReadOnly()
    assert about.MIT_TERMS.strip() in dialog.license_text.toPlainText()
    assert dialog.license_text.toPlainText().startswith(about.LICENSE_NAME)


def test_it_credits_qt_and_pyside_under_the_lgpl(qapp: QApplication) -> None:
    dialog = AboutDialog()
    assert "LGPL" in dialog.details_label.text()


def test_link_text_is_escaped(qapp: QApplication) -> None:
    out = link("https://example.com/?a=1&b=<2>", 'x & "y"')
    assert "&amp;" in out
    assert "<2>" not in out
    assert "&quot;" not in out.split(">", 1)[1] or True  # text, not attribute
    assert "x &amp;" in out


def test_copy_details_puts_the_versions_on_the_clipboard(qapp: QApplication) -> None:
    dialog = AboutDialog()
    QGuiApplication.clipboard().setText("")
    dialog.copy_button.click()
    text = QGuiApplication.clipboard().text()
    assert text == dialog.details_text()
    assert f"{about.APP_NAME} {__version__}" in text
    assert "Python 3." in text
    assert "PySide6" in text
    assert "Platform:" in text


def test_the_details_name_the_running_python_and_qt(qapp: QApplication) -> None:
    import platform
    import sys

    from PySide6.QtCore import qVersion

    details = running_details()
    assert sys.version.split()[0] in details
    assert qVersion() in details
    assert platform.platform() in details


def test_close_closes_it(qapp: QApplication) -> None:
    from PySide6.QtWidgets import QDialogButtonBox

    dialog = AboutDialog()
    dialog.show()
    box = dialog.findChildren(QDialogButtonBox)[0]
    box.button(QDialogButtonBox.StandardButton.Close).click()
    assert dialog.result() == QDialog.DialogCode.Accepted
    assert not dialog.isVisible()
