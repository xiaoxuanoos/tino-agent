"""The branded desktop updater must find the bundle electron-builder emits."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import psutil
import pytest

from hermes_cli import doctor_platform, gui_uninstall, main_desktop


def _make_executable(root: Path, relative: str) -> Path:
    executable = root / relative
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_bytes(b"test executable")
    return executable


def test_branded_macos_bundle_wins_over_legacy_bundle(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    current = _make_executable(
        tmp_path, "mac-arm64/Tino Agent.app/Contents/MacOS/Tino Agent"
    )
    legacy = _make_executable(tmp_path, "mac-arm64/Tino.app/Contents/MacOS/Tino")
    os.utime(legacy, (current.stat().st_mtime + 60, current.stat().st_mtime + 60))

    assert main_desktop._desktop_packaged_executable_in(tmp_path) == current


def test_branded_windows_and_linux_executables_are_found(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    windows = _make_executable(tmp_path, "win-unpacked/Tino Agent.exe")
    assert main_desktop._desktop_packaged_executable_in(tmp_path) == windows

    monkeypatch.setattr(sys, "platform", "linux")
    linux = _make_executable(tmp_path, "linux-unpacked/Tino Agent")
    assert main_desktop._desktop_packaged_executable_in(tmp_path) == linux


def test_running_branded_macos_bundle_is_not_treated_as_idle(tmp_path, monkeypatch):
    branded = _make_executable(tmp_path, "Tino Agent.app/Contents/MacOS/Tino Agent")
    other = _make_executable(tmp_path, "Other.app/Contents/MacOS/Other")
    processes = [SimpleNamespace(info={"exe": str(path)}) for path in (branded, other)]
    monkeypatch.setattr(psutil, "process_iter", lambda _attrs: processes)

    assert main_desktop._running_macos_app_bundles() == {branded.parents[2]}


def test_installed_branded_macos_paths_are_known(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    paths = gui_uninstall.packaged_gui_app_paths()

    assert Path("/Applications/Tino Agent.app") in paths
    assert Path.home() / "Applications" / "Tino Agent.app" in paths


def test_doctor_discovers_branded_macos_bundle(tmp_path, monkeypatch):
    module = tmp_path / "hermes_cli" / "doctor_platform.py"
    monkeypatch.setattr(doctor_platform, "__file__", str(module))
    branded = tmp_path / "apps" / "desktop" / "release" / "mac-arm64" / "Tino Agent.app"
    branded.mkdir(parents=True)

    assert doctor_platform._desktop_app_bundle() == branded


def test_failed_macos_signing_keeps_existing_branded_app(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "platform", "darwin")
    desktop = tmp_path / "apps" / "desktop"
    live = _make_executable(
        desktop / "release", "mac-arm64/Tino Agent.app/Contents/MacOS/Tino Agent"
    )
    live.write_text("working app", encoding="utf-8")
    staging = desktop / ".staging-test"
    staged = _make_executable(
        staging, "mac-arm64/Tino Agent.app/Contents/MacOS/Tino Agent"
    )
    staged.write_text("unsigned app", encoding="utf-8")
    monkeypatch.setattr(main_desktop, "_desktop_macos_relaunchable_fixup", lambda *_a, **_kw: False)

    with pytest.raises(SystemExit) as error:
        main_desktop._promote_staged_desktop_app(desktop, staging)

    assert error.value.code == 1
    assert live.read_text(encoding="utf-8") == "working app"
    assert not staging.exists()
    assert "previous desktop app was left untouched" in capsys.readouterr().out
