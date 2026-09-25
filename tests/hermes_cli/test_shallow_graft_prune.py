"""Stale shallow-graft pruning after depth-1 update checks (#105951).

Every ``git fetch --depth 1`` appends the fetched tip to ``.git/shallow`` as a
new graft and never removes the previous one, so a long-lived shallow installer
checkout accumulates one line per update check (57 observed in the wild). The
stale grafts break ``merge-base`` and push ``hermes update`` into the
orphan-divergence reset path. ``prune_stale_shallow_grafts()`` drops grafts no
live ref points at; ``hermes update --check`` calls it after its successful
depth-1 fetch, clearing the grafts accumulated by past checks (the passive
banner check no longer git-fetches since #107648).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from hermes_cli.gitlock import prune_stale_shallow_grafts

SHA_A = "a" * 40
SHA_B = "b" * 40


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _shallow_lines(repo: Path) -> list:
    return [
        line for line in (repo / ".git" / "shallow").read_text().splitlines() if line
    ]


def _mk_shallow_scenario(tmp_path: Path) -> Path:
    """Depth-1 clone whose origin advanced twice: shallow carries 3 grafts."""
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-q", "-b", "main")
    _git(origin, "config", "user.email", "t@example.com")
    _git(origin, "config", "user.name", "t")
    for i in range(3):
        _git(origin, "commit", "--allow-empty", "-q", "-m", f"c{i}")
    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", f"file://{origin}", str(clone)],
        check=True,
        capture_output=True,
        text=True,
    )
    for i in range(3, 5):
        _git(origin, "commit", "--allow-empty", "-q", "-m", f"c{i}")
        _git(clone, "fetch", "-q", "--depth", "1", "origin", "main")
    return clone


def test_prunes_orphaned_grafts_keeps_referenced_boundaries(tmp_path):
    clone = _mk_shallow_scenario(tmp_path)
    assert len(_shallow_lines(clone)) == 3  # HEAD graft + two fetched tips

    head_sha = _git(clone, "rev-parse", "HEAD")
    tip_sha = _git(clone, "rev-parse", "origin/main")

    removed = prune_stale_shallow_grafts(clone)

    assert removed == 1  # the middle, now-unreferenced tip
    assert set(_shallow_lines(clone)) == {head_sha, tip_sha}
    # Boundaries that survive must still walk cleanly.
    assert _git(clone, "rev-list", "--count", "HEAD") == "1"
    assert _git(clone, "rev-list", "--count", "origin/main") == "1"


def test_prune_is_idempotent_and_noop_without_grafts(tmp_path):
    clone = _mk_shallow_scenario(tmp_path)
    assert prune_stale_shallow_grafts(clone) == 1
    assert prune_stale_shallow_grafts(clone) == 0  # nothing left to drop

    empty_dir = tmp_path / "not-a-repo"
    empty_dir.mkdir()
    assert prune_stale_shallow_grafts(empty_dir) == 0  # not a git repo: no-op

    git_no_shallow = tmp_path / "full-clone"
    git_no_shallow.mkdir()
    (git_no_shallow / ".git").mkdir()
    assert prune_stale_shallow_grafts(git_no_shallow) == 0  # no shallow file: no-op


def test_update_check_prunes_and_reports_count(tmp_path, monkeypatch, capsys):
    """`hermes update --check` prunes grafts after its depth-1 fetch and reports the prune."""
    import hermes_cli.update_cmd as update_cmd

    fake_root = SimpleNamespace(PROJECT_ROOT=tmp_path)
    monkeypatch.setattr(update_cmd, "_m", lambda: fake_root)
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(
        "hermes_cli.update_contract.evaluate_update_admission", lambda root: None
    )
    monkeypatch.setattr(update_cmd, "_is_shallow_checkout", lambda git_cmd: True)
    monkeypatch.setattr(update_cmd, "_tip_shas", lambda git_cmd, branch: (SHA_A, SHA_B))

    def fake_git_run(git_cmd, args, **kwargs):
        joined = " ".join(args)
        if "get-url" in joined and "upstream" in joined:
            return MagicMock(returncode=1, stdout="", stderr="")  # no upstream remote
        if "fetch" in joined:
            return MagicMock(returncode=0, stdout="", stderr="")  # depth-1 fetch lands
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(update_cmd, "_git_run", fake_git_run)
    monkeypatch.setattr(update_cmd, "_base_git_cmd", lambda: ["git"])
    monkeypatch.setattr("hermes_cli.banner._github_compare_behind", lambda *a, **k: 0)
    prune_calls = []
    monkeypatch.setattr(
        "hermes_cli.gitlock.prune_stale_shallow_grafts",
        lambda repo: prune_calls.append(repo) or 2,
    )

    update_cmd._cmd_update_check("main")

    out = capsys.readouterr().out
    assert prune_calls == [tmp_path]
    assert "pruned 2 stale shallow graft(s)" in out


def _mk_depth_one_update(tmp_path: Path) -> tuple[Path, Path]:
    """An update check grafts the new tip although it descends from HEAD."""
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-q", "-b", "main")
    _git(origin, "config", "user.email", "t@example.com")
    _git(origin, "config", "user.name", "t")
    for i in range(2):
        _git(origin, "commit", "--allow-empty", "-q", "-m", f"c{i}")
    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", f"file://{origin}", str(clone)],
        check=True, capture_output=True, text=True,
    )
    _git(clone, "config", "user.email", "t@example.com")
    _git(clone, "config", "user.name", "t")
    _git(origin, "commit", "--allow-empty", "-q", "-m", "remote-new")
    _git(clone, "fetch", "-q", "--depth", "1", "origin", "main")
    assert len(_shallow_lines(clone)) == 2
    assert subprocess.run(
        ["git", "merge-base", "HEAD", "origin/main"],
        cwd=clone, capture_output=True,
    ).returncode != 0
    return origin, clone


def test_update_repairs_depth_one_check_before_fast_forward(tmp_path, monkeypatch):
    """The real `--check` graft must not send a direct descendant into reset."""
    import hermes_cli.update_cmd as update_cmd

    _, clone = _mk_depth_one_update(tmp_path)
    old_head = _git(clone, "rev-parse", "HEAD")
    monkeypatch.setattr(update_cmd, "_m", lambda: SimpleNamespace(PROJECT_ROOT=clone))

    update_cmd._connect_shallow_update_history(["git"], "main")

    assert _git(clone, "merge-base", "HEAD", "origin/main") == old_head
    _git(clone, "merge", "--ff-only", "origin/main")
    assert _git(clone, "rev-parse", "HEAD") == _git(clone, "rev-parse", "origin/main")


def test_update_preserves_local_commit_after_history_repair(tmp_path, monkeypatch, capsys):
    """A genuinely local commit survives a diverged update on the same branch."""
    import pytest
    import hermes_cli.update_cmd as update_cmd

    _, clone = _mk_depth_one_update(tmp_path)
    _git(clone, "commit", "--allow-empty", "-q", "-m", "local-unpushed")
    local_head = _git(clone, "rev-parse", "HEAD")
    monkeypatch.setattr(update_cmd, "_m", lambda: SimpleNamespace(PROJECT_ROOT=clone))

    update_cmd._connect_shallow_update_history(["git"], "main")
    with pytest.raises(SystemExit, match="1"):
        update_cmd._reconcile_diverged_checkout(["git"], "main", local_head)

    assert _git(clone, "rev-parse", "HEAD") == local_head
    assert "No commits were reset" in capsys.readouterr().out


def test_update_stops_on_unrelated_shallow_history(tmp_path, monkeypatch, capsys):
    """No amount of deepening should reset an orphaned local checkout."""
    import pytest
    import hermes_cli.update_cmd as update_cmd

    origin, clone = _mk_depth_one_update(tmp_path)
    local_head = _git(clone, "rev-parse", "HEAD")
    _git(origin, "checkout", "-q", "--orphan", "replacement")
    _git(origin, "commit", "--allow-empty", "-q", "-m", "unrelated")
    _git(origin, "branch", "-D", "main")
    _git(origin, "branch", "-m", "main")
    _git(clone, "fetch", "-q", "--depth", "1", "origin", "main")
    monkeypatch.setattr(update_cmd, "_m", lambda: SimpleNamespace(PROJECT_ROOT=clone))

    with pytest.raises(SystemExit, match="1"):
        update_cmd._connect_shallow_update_history(["git"], "main")

    assert _git(clone, "rev-parse", "HEAD") == local_head
    assert "no local commits were reset" in capsys.readouterr().out.lower()


def test_failed_fast_forward_keeps_untracked_file(tmp_path, monkeypatch, capsys):
    """An untracked-file conflict is not permission to reset the checkout."""
    import pytest
    import hermes_cli.update_cmd as update_cmd

    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-q", "-b", "main")
    _git(origin, "config", "user.email", "t@example.com")
    _git(origin, "config", "user.name", "t")
    _git(origin, "commit", "--allow-empty", "-q", "-m", "base")
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True)
    old_head = _git(clone, "rev-parse", "HEAD")
    (origin / "notes.txt").write_text("remote\n")
    _git(origin, "add", "notes.txt")
    _git(origin, "commit", "-q", "-m", "add notes")
    (clone / "notes.txt").write_text("user's untracked work\n")
    _git(clone, "fetch", "-q", "origin", "main")

    failed_merge = subprocess.run(
        ["git", "merge", "--ff-only", "origin/main"],
        cwd=clone, capture_output=True, text=True,
    )
    assert failed_merge.returncode != 0
    monkeypatch.setattr(update_cmd, "_m", lambda: SimpleNamespace(PROJECT_ROOT=clone))
    with pytest.raises(SystemExit, match="1"):
        update_cmd._reconcile_diverged_checkout(
            ["git"], "main", old_head, merge_failure=failed_merge)

    assert _git(clone, "rev-parse", "HEAD") == old_head
    assert (clone / "notes.txt").read_text() == "user's untracked work\n"
    assert "no commits or files were reset" in capsys.readouterr().out
