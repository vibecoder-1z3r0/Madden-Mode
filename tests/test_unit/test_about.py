"""The About window's facts, checked against the repository files they come from."""

import re
import tomllib
from pathlib import Path

import pytest
from packaging.version import Version

from maddenmode import __version__, about

ROOT = Path(__file__).resolve().parents[2]


def read(name: str) -> str:
    return (ROOT / name).read_text()


def squash(text: str) -> str:
    return " ".join(text.split())


# -- the version -------------------------------------------------------------------

CALVER = re.compile(r"^\d{4}\.([1-9]|1[0-2])\.\d+((a|b|rc)\d+)?$")


def test_the_version_is_a_calendar_version() -> None:
    assert CALVER.match(__version__), __version__
    assert int(__version__.split(".")[0]) >= 2026


def test_the_version_is_written_the_way_python_normalises_it() -> None:
    # a zero-padded month would be rewritten by pip (2026.01.0 -> 2026.1.0),
    # leaving the app and the installed package disagreeing
    assert str(Version(__version__)) == __version__


def test_the_about_window_uses_the_package_version() -> None:
    assert about.VERSION == __version__


def test_the_version_is_defined_in_one_place() -> None:
    project = tomllib.loads(read("pyproject.toml"))
    assert "version" not in project["project"]  # no second copy to forget
    assert "version" in project["project"]["dynamic"]
    source = ROOT / project["tool"]["hatch"]["version"]["path"]
    assert f'__version__ = "{__version__}"' in source.read_text()


def test_the_installed_package_reports_the_same_version() -> None:
    from importlib.metadata import version

    # fails if pyproject and the code ever drift, or `uv sync` was not re-run
    assert version("madden-mode") == __version__


@pytest.mark.parametrize(
    ("version", "stage"),
    [
        ("2026.11.0a1", "alpha"),
        ("2026.11.0a12", "alpha"),
        ("2026.12.0b2", "beta"),
        ("2027.1.0rc1", "release candidate"),
        ("2027.1.0", None),
        ("2027.1.3", None),
    ],
)
def test_the_release_stage(version: str, stage: str | None) -> None:
    assert about.release_stage(version) == stage


def test_the_version_label_says_alpha() -> None:
    assert about.version_label("2026.11.0a1") == "Version 2026.11.0a1 (alpha)"
    assert about.version_label("2027.1.0") == "Version 2027.1.0"


def test_a_pre_release_gets_a_plain_language_note_and_a_full_release_does_not() -> None:
    note = about.stage_note("2026.11.0a1")
    assert note is not None and "alpha" in note and "rough edges" in note
    assert about.stage_note("2027.1.0") is None


def test_the_classifier_matches_the_stage() -> None:
    classifiers = tomllib.loads(read("pyproject.toml"))["project"]["classifiers"]
    wanted = {"alpha": "3 - Alpha", "beta": "4 - Beta"}.get(about.release_stage() or "")
    if wanted:
        assert f"Development Status :: {wanted}" in classifiers


# -- the AI Attribution statement ------------------------------------------------------


def test_aia_url_rebuilds_the_link_the_projects_old_commits_used() -> None:
    # copied from a commit in the many-game-show repository
    old = "AIA PAI SeCeNc Hin R Claude Code Web Sonnet 5 Medium v1.0"
    assert about.aia_url(old) == (
        "https://aiattribution.github.io/statements/"
        "AIA-PAI-SeCeNc-Hin-R-?model=Claude+Code+Web+Sonnet+5+Medium-v1.0"
    )


def test_the_aia_link_for_this_project() -> None:
    assert about.aia_url() == (
        "https://aiattribution.github.io/statements/"
        "AIA-PAI-SeCeNc-Hin-R-?model=Claude+Code+Web+Sonnet+5.5+Medium-v1.0"
    )


@pytest.mark.parametrize("bad", ["", "AIA", "PAI SeCeNc Hin R Claude v1.0", "AIA a b"])
def test_aia_url_rejects_something_that_is_not_a_statement(bad: str) -> None:
    with pytest.raises(ValueError):
        about.aia_url(bad)


def test_both_aia_statements_are_the_ones_in_the_attribution_doc() -> None:
    doc = read("AIA_ATTRIBUTION.md")
    assert about.AIA_STATEMENT in doc
    assert about.AIA_ABBREVIATED in doc


def test_the_commit_convention_uses_the_same_abbreviated_statement() -> None:
    assert about.AIA_ABBREVIATED in read("CONTRIBUTING.md")


# -- the license and the people ------------------------------------------------------


def test_the_license_name_and_copyright_are_the_ones_in_license() -> None:
    lines = read("LICENSE").splitlines()
    assert lines[0] == about.LICENSE_NAME
    assert about.COPYRIGHT in lines


def test_the_mit_terms_are_the_ones_in_license() -> None:
    assert squash(about.MIT_TERMS) in squash(read("LICENSE"))


def test_the_license_summary_is_short_and_plain() -> None:
    assert "warranty" in about.MIT_SUMMARY
    assert len(about.MIT_SUMMARY) < 140


def test_the_github_links_agree_with_the_readme_and_each_other() -> None:
    assert f"git clone {about.REPO_URL}" in read("README.md")
    assert about.REPO_URL.startswith(about.OWNER_URL + "/")
    assert about.REPO_LICENSE_URL == about.REPO_URL + "/blob/main/LICENSE"


def test_the_owner_name_matches_the_commit_trailers() -> None:
    assert f"Vibe-Coder: {about.OWNER_NAME} <" in read("CONTRIBUTING.md")


def test_qt_is_credited_under_the_lgpl() -> None:
    assert "LGPL" in about.NOTICE_QT
    assert "PySide6" in about.NOTICE_QT


def test_the_bug_report_details() -> None:
    text = about.details_text("3.13.1", "6.12.0", "6.12.0", "Windows-11")
    assert text.splitlines() == [
        f"Madden Mode {__version__}",
        "Python 3.13.1",
        "Qt 6.12.0 (PySide6 6.12.0)",
        "Platform: Windows-11",
    ]
