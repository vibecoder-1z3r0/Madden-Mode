#!/usr/bin/env python3
"""Preflight check for developing or running Madden Mode on a machine.

Ported from many-game-show's preflight.sh, but written in Python (standard
library only) so it runs the same on Windows, macOS and Linux without bash.
Run it with the system Python, before `uv sync`:

    python3 scripts/preflight.py        (or `make preflight`)

Checks host-level prerequisites that `uv sync` does NOT handle for you.
Exit code 0 = ready, 1 = something needs fixing first (see output).
"""

import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
counts = {"ok": 0, "warn": 0, "fail": 0}


def report(level: str, message: str) -> None:
    counts[level] += 1
    print(f"  {level.upper():<4} {message}")


def run(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT, check=False
    )


def check_tools() -> None:
    print("-- Required tools --")
    uv = shutil.which("uv")
    if uv:
        version = run([uv, "--version"]).stdout.strip()
        report("ok", f"uv found ({version})")
    else:
        report("fail", "uv not found: see https://docs.astral.sh/uv/")
    if shutil.which("git"):
        report("ok", "git found")
    else:
        report("fail", "git not found: needed to clone and update the repo")
    # This script runs on the system Python, which may be older than the
    # project's 3.13 floor, so the comparison is intentionally not static.
    running = tuple(sys.version_info[:2])
    if running >= (3, 13):
        report("ok", f"Python {platform.python_version()} (>= 3.13)")
    else:
        report(
            "warn",
            f"system Python is {platform.python_version()}; the project needs "
            "3.13+, which uv can install and manage for you",
        )


def check_network() -> None:
    print("\n-- Network reachability --")
    try:
        urllib.request.urlopen("https://pypi.org", timeout=5)  # noqa: S310
        report("ok", "PyPI reachable")
    except OSError as err:
        report("fail", f"PyPI NOT reachable ({err}): needed for `uv sync`")


def check_project() -> None:
    print("\n-- Project environment --")
    if (ROOT / "uv.lock").exists():
        report("ok", "uv.lock present (reproducible installs)")
    else:
        report("warn", "uv.lock missing: `uv sync` will generate one")
    if (ROOT / ".venv").is_dir():
        report("ok", ".venv exists")
        uv = shutil.which("uv")
        if uv:
            probe = run([uv, "run", "python", "-c", "import PySide6.QtGui"])
            if probe.returncode == 0:
                report("ok", "PySide6 (Qt) imports correctly")
            else:
                tail = probe.stderr.strip().splitlines()[-1:] or ["unknown error"]
                report("fail", f"PySide6 failed to import: {tail[0]}")
                if platform.system() == "Linux":
                    report("warn", "  on Linux try: make system-deps")
    else:
        report("warn", ".venv not created yet: run `make sync` first")


def check_display() -> None:
    print("\n-- Display (the overlay needs a graphical session) --")
    system = platform.system()
    if system == "Windows":
        report("ok", "Windows: primary target; layered click-through supported")
    elif system == "Darwin":
        report(
            "warn",
            "macOS: tests run in CI but it has never been tried by hand. There are "
            "no global hotkeys or window pinning yet, so use the toolbar",
        )
    elif system == "Linux":
        wayland = os.environ.get("WAYLAND_DISPLAY")
        x11 = os.environ.get("DISPLAY")
        if wayland:
            report(
                "warn",
                "Wayland session: always-on-top overlays and click-through "
                "are restricted; X11 (or XWayland) is more reliable",
            )
        elif x11:
            report("ok", f"X11 display available ({x11})")
        else:
            report("warn", "no display: GUI tests need a virtual one (xvfb)")
        if shutil.which("xvfb-run"):
            report("ok", "xvfb-run found (headless GUI tests)")
        else:
            report("warn", "xvfb-run not found: run `make system-deps`")
    else:
        report("warn", f"unsupported platform: {system}")


def main() -> int:
    print("Madden Mode: preflight check")
    print("=" * 29 + "\n")
    check_tools()
    check_network()
    check_project()
    check_display()
    print("\n" + "=" * 29)
    ok, warn, fail = counts["ok"], counts["warn"], counts["fail"]
    print(f"Passed: {ok}   Warnings: {warn}   Failed: {fail}")
    if counts["fail"]:
        print("\nFix the FAIL items above, then re-run.")
        return 1
    print("\nReady for: make sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
