"""The facts shown in the About window, in one place. No Qt.

Each of these is checked by a test against the file it comes from (LICENSE,
pyproject.toml, AIA_ATTRIBUTION.md, the README), so the window cannot drift
away from the repository.
"""

import re

from maddenmode import __version__

APP_NAME = "Madden Mode"
VERSION = __version__
TAGLINE = (
    "Telestration technology over your favorite game/window. "
    "Named after the greatest NFL sports casters in the honor of John Madden."
)

# Python writes an alpha, beta or release-candidate version as a suffix: 1a2 is alpha 2, 1b1 beta 1,
# 1rc1 release candidate 1.
_STAGES = {"a": "alpha", "b": "beta", "rc": "release candidate"}
_STAGE_PATTERN = re.compile(r"(a|b|rc)\d+$")


def release_stage(version: str = VERSION) -> str | None:
    """'alpha', 'beta' or 'release candidate' for a pre-release; None otherwise."""
    match = _STAGE_PATTERN.search(version)
    return _STAGES[match.group(1)] if match else None


def version_label(version: str = VERSION) -> str:
    """e.g. 'Version 2026.11.0a1 (alpha)'."""
    stage = release_stage(version)
    return f"Version {version}" + (f" ({stage})" if stage else "")


def stage_note(version: str = VERSION) -> str | None:
    """A plain-language heads-up for an alpha or beta, or None for no suffix."""
    stage = release_stage(version)
    if stage is None:
        return None
    return f"This is {stage} software: it works, but expect rough edges."


OWNER_NAME = "Vibe-Coder 1.z3r0"
OWNER_URL = "https://github.com/vibecoder-1z3r0"
REPO_URL = "https://github.com/vibecoder-1z3r0/Madden-Mode"
REPO_LICENSE_URL = f"{REPO_URL}/blob/main/LICENSE"

LICENSE_NAME = "MIT License"
COPYRIGHT = f"Copyright (c) 2026 {OWNER_NAME}"
MIT_TERMS = """\
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
MIT_SUMMARY = (
    "Free to use, copy, modify and share, with no warranty. "
    "Keep the copyright notice with any copy."
)

# The AI Attribution statement for this project (see AIA_ATTRIBUTION.md).
AIA_ABBREVIATED = "AIA PAI SeCeNc Hin R Claude Code Web Sonnet 5.5 Medium v1.0"
AIA_STATEMENT = (
    "AIA Primarily AI, Stylistic edits, Content edits, New content, "
    "Human-initiated, Reviewed, Claude Code Web Sonnet 5.5 Medium v1.0"
)
AIA_BASE_URL = "https://aiattribution.github.io/statements/"


def aia_url(abbreviated: str = AIA_ABBREVIATED) -> str:
    """The AI Attribution page for a statement, built the way our commits did.

    'AIA PAI SeCeNc Hin R Claude Code Web Sonnet 5 Medium v1.0' becomes
    '.../AIA-PAI-SeCeNc-Hin-R-?model=Claude+Code+Web+Sonnet+5+Medium-v1.0'.

    The pattern comes from this project's earlier commits; the AIA site could
    not be reached from where this was written, so it has not been opened.
    """
    parts = abbreviated.split()
    if len(parts) < 7 or parts[0] != "AIA":
        raise ValueError(f"not an abbreviated AIA statement: {abbreviated!r}")
    code = "-".join(parts[1:5])  # PAI-SeCeNc-Hin-R
    model = "+".join(parts[5:-1]) + "-" + parts[-1]  # ...+Medium-v1.0
    return f"{AIA_BASE_URL}AIA-{code}-?model={model}"


NOTICE_QT = (
    "Built with Python and Qt, through PySide6. Qt and PySide6 are used under "
    "the GNU LGPL v3."
)


def details_text(
    python: str, qt: str, pyside: str, platform: str, version: str = VERSION
) -> str:
    """Plain text for a bug report: what is running and on what."""
    return "\n".join(
        [
            f"{APP_NAME} {version}",
            f"Python {python}",
            f"Qt {qt} (PySide6 {pyside})",
            f"Platform: {platform}",
        ]
    )
