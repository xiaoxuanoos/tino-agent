"""Desktop updates accept both managed ``venv`` and source ``.venv`` layouts."""

from __future__ import annotations

from pathlib import Path
import os
import subprocess

import pytest


POSIX_SH = Path(__file__).resolve().parents[3] / "scripts" / "desktop-update" / "posix.sh"


def _resolve(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(POSIX_SH), "--self-test-venv-resolver", "--install-root", str(root)],
        capture_output=True,
        text=True,
    )


def _hermes(root: Path, venv_name: str) -> Path:
    executable = root / venv_name / "bin" / "hermes"
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(0o755)
    return executable


def test_source_dot_venv_is_accepted(tmp_path: Path) -> None:
    expected = _hermes(tmp_path, ".venv").parents[1]
    result = _resolve(tmp_path)
    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()) == expected


def test_managed_venv_wins_when_both_exist(tmp_path: Path) -> None:
    expected = _hermes(tmp_path, "venv").parents[1]
    _hermes(tmp_path, ".venv")
    result = _resolve(tmp_path)
    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()) == expected


def test_missing_entrypoints_fail_closed(tmp_path: Path) -> None:
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    result = _resolve(tmp_path)
    assert result.returncode == 1
    assert result.stdout == ""


@pytest.mark.parametrize("isolated_home", [True, False])
def test_handoff_marker_uses_the_same_home_as_desktop(tmp_path: Path, isolated_home: bool) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    runtime_home = tmp_path / "isolated" if isolated_home else tmp_path
    runtime_home.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.pop("TINO_HOME", None)
    if isolated_home:
        env["TINO_HOME"] = str(runtime_home)

    result = subprocess.run(
        [
            "bash", str(POSIX_SH), "--daemonized", "--self-test-marker",
            "--install-root", str(checkout),
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    marker = runtime_home / ".hermes-update-in-progress"
    assert marker.exists()
    assert marker.read_text(encoding="utf-8").splitlines()[0].isdigit()
    if isolated_home:
        assert not (tmp_path / ".hermes-update-in-progress").exists()
