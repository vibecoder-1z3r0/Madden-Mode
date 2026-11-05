#!/usr/bin/env python3
"""Install the system libraries Qt needs on Linux.

    python3 scripts/system_deps.py [--dry-run]        (or `make system-deps`)

Reads /etc/os-release to find the distro family and uses its package manager:

- Debian, Ubuntu and relatives: apt
- Fedora, RHEL and relatives:   dnf

Other Linux distros get a clear message listing what is needed. macOS and
Windows need nothing. Verified on Ubuntu only; the Fedora package names are
from memory and have not been tried on a Fedora machine.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# What Qt needs to load, plus Xvfb for running GUI tests without a display.
PACKAGES: dict[str, list[str]] = {
    "apt": [
        "libegl1",
        "libgl1",
        "libxkbcommon0",
        "libxkbcommon-x11-0",
        "libdbus-1-3",
        "libfontconfig1",
        "xvfb",
        "libxcb-cursor0",
        "libxcb-icccm4",
        "libxcb-image0",
        "libxcb-keysyms1",
        "libxcb-render-util0",
        "libxcb-xinerama0",
        "libxcb-xkb1",
        "libxcb-shape0",
    ],
    "dnf": [
        "mesa-libEGL",
        "mesa-libGL",
        "libxkbcommon",
        "libxkbcommon-x11",
        "dbus-libs",
        "fontconfig",
        "xorg-x11-server-Xvfb",
        "xcb-util-cursor",
        "xcb-util-wm",
        "xcb-util-image",
        "xcb-util-keysyms",
        "xcb-util-renderutil",
        "libxcb",
    ],
}

# Distro IDs (from ID and ID_LIKE in /etc/os-release) for each package manager.
FAMILIES: dict[str, set[str]] = {
    "apt": {"debian", "ubuntu"},
    "dnf": {"fedora", "rhel", "centos", "rocky", "almalinux"},
}

GENERIC_NEEDS = (
    "EGL and OpenGL, xkbcommon (and its X11 part), D-Bus, fontconfig, Xvfb, and the "
    "xcb-util libraries (cursor, icccm, image, keysyms, renderutil) plus libxcb"
)


def parse_os_release(text: str) -> dict[str, str]:
    info: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        info[key] = value.strip().strip('"').strip("'")
    return info


def detect_manager(info: dict[str, str]) -> str | None:
    """The package manager for this distro, or None if we do not know it."""
    ids = [info.get("ID", ""), *info.get("ID_LIKE", "").split()]
    for distro in (i.lower() for i in ids if i):
        for manager, family in FAMILIES.items():
            if distro in family:
                return manager
    return None


def commands(manager: str, sudo: list[str]) -> list[list[str]]:
    packages = PACKAGES[manager]
    if manager == "apt":
        return [
            [*sudo, "apt-get", "update"],
            [*sudo, "apt-get", "install", "-y", *packages],
        ]
    return [[*sudo, "dnf", "install", "-y", *packages]]


def running_as_root() -> bool:
    return hasattr(os, "geteuid") and os.geteuid() == 0


def has_sudo() -> bool:
    return shutil.which("sudo") is not None


def sudo_prefix(is_root: bool, has_sudo: bool) -> list[str]:
    if is_root:
        return []
    if has_sudo:
        return ["sudo"]
    raise SystemExit("Installing packages needs root: run as root or install sudo.")


def main(
    argv: list[str] | None = None,
    os_release: Path = Path("/etc/os-release"),
    platform: str = sys.platform,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dry-run", action="store_true", help="print the commands without running"
    )
    args = parser.parse_args(argv)

    if not platform.startswith("linux"):
        print(f"No system libraries to install on {platform}.")
        return 0

    try:
        info = parse_os_release(os_release.read_text())
    except OSError:
        info = {}
    manager = detect_manager(info)
    name = info.get("PRETTY_NAME") or info.get("ID") or "this Linux distro"
    if manager is None:
        print(
            f"Don't know the package manager for {name}.\n"
            f"Install the equivalents of: {GENERIC_NEEDS}.\n"
            "apt (Debian, Ubuntu) and dnf (Fedora, RHEL) are supported here."
        )
        return 1

    sudo = sudo_prefix(running_as_root(), has_sudo())
    print(f"Detected {name}: using {manager}.")
    for command in commands(manager, sudo):
        print("+", " ".join(command))
        if args.dry_run:
            continue
        code = subprocess.run(command, check=False).returncode
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main())
