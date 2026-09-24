"""The macOS updater must not copy a rebuilt app over itself through a symlink."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.macos_only
POSIX_SH = Path(__file__).resolve().parents[3] / "scripts" / "desktop-update" / "posix.sh"


def _same_bundle(first: Path, second: Path, state: Path) -> str:
    result = subprocess.run(
        ["bash", str(POSIX_SH), "--self-test-mac-path-equality", "--install-root", str(first),
         "--relaunch-target", str(second)],
        capture_output=True, text=True, check=True,
        env={**os.environ, "TINO_HOME": str(state)},
    )
    return result.stdout.strip()


def test_symlink_and_physical_app_are_same_bundle(tmp_path):
    physical = tmp_path / "local-build" / "release" / "mac-arm64" / "Tino Agent.app"
    physical.mkdir(parents=True)
    checkout_release = tmp_path / "checkout" / "apps" / "desktop" / "release"
    checkout_release.parent.mkdir(parents=True)
    checkout_release.symlink_to(physical.parents[1], target_is_directory=True)
    linked = checkout_release / "mac-arm64" / "Tino Agent.app"

    assert _same_bundle(linked, physical, tmp_path / "state") == "same"


def test_different_apps_are_not_same_bundle(tmp_path):
    first = tmp_path / "first" / "Tino Agent.app"
    second = tmp_path / "second" / "Tino Agent.app"
    first.mkdir(parents=True)
    second.mkdir(parents=True)

    assert _same_bundle(first, second, tmp_path / "state") == "different"
