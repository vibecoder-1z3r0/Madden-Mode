"""Tests for scripts/system_deps.py (distro detection and the commands it runs)."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "system_deps.py"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("system_deps", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sd = load()


@pytest.fixture(autouse=True)
def pretend_to_be_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the tests independent of the machine they run on.

    The script asks "am I root?" and "is sudo installed?". Those answers differ
    between Linux, macOS and Windows (os.geteuid does not exist on Windows, and
    sudo is not installed there), so each test states them instead.
    """
    monkeypatch.setattr(sd, "running_as_root", lambda: True)
    monkeypatch.setattr(sd, "has_sudo", lambda: True)


UBUNTU = 'NAME="Ubuntu"\nID=ubuntu\nID_LIKE=debian\nPRETTY_NAME="Ubuntu 24.04 LTS"\n'
DEBIAN = 'PRETTY_NAME="Debian GNU/Linux 12"\nID=debian\n'
POP = 'ID=pop\nID_LIKE="ubuntu debian"\n'
FEDORA = 'NAME="Fedora Linux"\nID=fedora\nPRETTY_NAME="Fedora Linux 41"\n'
ROCKY = 'ID="rocky"\nID_LIKE="rhel centos fedora"\n'
RHEL = 'ID="rhel"\nID_LIKE="fedora"\n'
ARCH = "ID=arch\n"
NIXOS = "ID=nixos\n"


@pytest.mark.parametrize(
    ("text", "manager"),
    [
        (UBUNTU, "apt"),
        (DEBIAN, "apt"),
        (POP, "apt"),  # unknown ID, recognised through ID_LIKE
        (FEDORA, "dnf"),
        (ROCKY, "dnf"),
        (RHEL, "dnf"),
        (ARCH, None),
        (NIXOS, None),
        ("", None),
    ],
)
def test_detects_the_package_manager(text: str, manager: str | None) -> None:
    assert sd.detect_manager(sd.parse_os_release(text)) == manager


def test_parse_handles_quotes_comments_and_blank_lines() -> None:
    info = sd.parse_os_release(
        "# a comment\n\nID=\"fedora\"\nNAME='Fedora'\nbroken line\n"
    )
    assert info == {"ID": "fedora", "NAME": "Fedora"}


def test_detection_is_case_insensitive() -> None:
    assert sd.detect_manager({"ID": "Fedora"}) == "dnf"


def test_apt_updates_first_then_installs_every_package() -> None:
    update, install = sd.commands("apt", ["sudo"])
    assert update == ["sudo", "apt-get", "update"]
    assert install[:4] == ["sudo", "apt-get", "install", "-y"]
    assert install[4:] == sd.PACKAGES["apt"]


def test_dnf_installs_every_package_in_one_command() -> None:
    (install,) = sd.commands("dnf", [])
    assert install[:3] == ["dnf", "install", "-y"]
    assert install[3:] == sd.PACKAGES["dnf"]


def test_the_ubuntu_package_list_is_the_one_ci_depends_on() -> None:
    # CI installs these through `make system-deps`; losing one breaks Qt there.
    for package in ("libegl1", "libxcb-cursor0", "xvfb", "libxkbcommon-x11-0"):
        assert package in sd.PACKAGES["apt"]


def test_package_lists_have_no_duplicates_and_cover_the_same_needs() -> None:
    for packages in sd.PACKAGES.values():
        assert len(packages) == len(set(packages))
    assert any("Xvfb" in p or p == "xvfb" for p in sd.PACKAGES["dnf"])
    assert any("Xvfb" in p or p == "xvfb" for p in sd.PACKAGES["apt"])


def test_every_family_has_a_package_list() -> None:
    assert set(sd.FAMILIES) == set(sd.PACKAGES)


def test_root_needs_no_sudo_and_others_use_it() -> None:
    assert sd.sudo_prefix(is_root=True, has_sudo=True) == []
    assert sd.sudo_prefix(is_root=False, has_sudo=True) == ["sudo"]
    with pytest.raises(SystemExit):
        sd.sudo_prefix(is_root=False, has_sudo=False)


def run(
    tmp_path: Path, text: str | None, capsys, *args: str, platform: str = "linux"
) -> tuple[int, str]:  # type: ignore[no-untyped-def]
    release = tmp_path / "os-release"
    if text is not None:
        release.write_text(text)
    code = sd.main(list(args), os_release=release, platform=platform)
    return code, capsys.readouterr().out


def test_dry_run_on_fedora_prints_dnf_and_runs_nothing(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    code, out = run(tmp_path, FEDORA, capsys, "--dry-run")
    assert code == 0
    assert "Fedora Linux 41" in out
    assert "dnf install -y" in out
    assert "apt-get" not in out


def test_dry_run_on_ubuntu_prints_apt(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    code, out = run(tmp_path, UBUNTU, capsys, "--dry-run")
    assert code == 0
    assert "apt-get update" in out
    assert "apt-get install -y" in out
    assert "dnf" not in out


def test_an_unknown_distro_gets_a_helpful_message_and_a_failure(
    tmp_path: Path, capsys
) -> None:  # type: ignore[no-untyped-def]
    code, out = run(tmp_path, ARCH, capsys, "--dry-run")
    assert code == 1
    assert "apt" in out and "dnf" in out
    assert "xcb-util" in out


def test_a_missing_os_release_is_treated_as_unknown(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    code, _ = run(tmp_path, None, capsys, "--dry-run")
    assert code == 1


@pytest.mark.parametrize("platform", ["win32", "darwin"])
def test_other_platforms_need_nothing(tmp_path: Path, capsys, platform: str) -> None:  # type: ignore[no-untyped-def]
    code, out = run(tmp_path, UBUNTU, capsys, platform=platform)
    assert code == 0
    assert "No system libraries" in out


def test_a_failing_command_stops_and_returns_its_exit_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    ran: list[list[str]] = []

    class Result:
        returncode = 7

    def fake_run(command: list[str], check: bool) -> Result:
        ran.append(command)
        return Result()

    monkeypatch.setattr(sd.subprocess, "run", fake_run)
    code, _ = run(tmp_path, UBUNTU, capsys)
    assert code == 7
    assert len(ran) == 1  # `apt-get update` failed, so no install was attempted


def test_all_commands_run_when_all_succeed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    ran: list[list[str]] = []

    class Result:
        returncode = 0

    monkeypatch.setattr(
        sd.subprocess, "run", lambda command, check: (ran.append(command), Result())[1]
    )
    code, _ = run(tmp_path, UBUNTU, capsys)
    assert code == 0
    assert [c[:2] for c in ran] == [["apt-get", "update"], ["apt-get", "install"]]


def test_a_non_root_user_with_sudo_gets_sudo_in_every_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    monkeypatch.setattr(sd, "running_as_root", lambda: False)
    code, out = run(tmp_path, UBUNTU, capsys, "--dry-run")
    assert code == 0
    assert "+ sudo apt-get update" in out
    assert "+ sudo apt-get install -y" in out


def test_a_non_root_user_without_sudo_is_told_what_to_do(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    monkeypatch.setattr(sd, "running_as_root", lambda: False)
    monkeypatch.setattr(sd, "has_sudo", lambda: False)
    with pytest.raises(SystemExit, match="root"):
        run(tmp_path, UBUNTU, capsys, "--dry-run")


def test_the_real_root_check_does_not_need_geteuid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Windows has no os.geteuid: the real helper must not raise there
    monkeypatch.undo()  # drop the autouse stand-ins to test the real functions
    monkeypatch.delattr(sd.os, "geteuid", raising=False)
    assert sd.running_as_root() is False
