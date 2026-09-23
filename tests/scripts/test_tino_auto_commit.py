"""Actual Git operations in a disposable repository exercise the commit boundary."""

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[2] / "scripts" / "tino_auto_commit.py"
SPEC = importlib.util.spec_from_file_location("tino_auto_commit", SOURCE)
AUTOCOMMIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUTOCOMMIT)
REPO = "tino-owner/tino-agent"


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, text=True, capture_output=True).stdout.strip()


class TinoCommitTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.repo = Path(self.directory.name)
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.name", "Tino Test")
        git(self.repo, "config", "user.email", "tino-test@example.invalid")
        git(self.repo, "remote", "add", "origin", f"https://github.com/{REPO}.git")
        (self.repo / "tests").mkdir()
        (self.repo / "scripts").mkdir()
        (self.repo / "tests" / "test_ok.py").write_text("def test_ok(): pass\n")
        runner = self.repo / "scripts" / "run_tests.sh"
        runner.write_text("#!/bin/sh\nexit 0\n")
        runner.chmod(0o755)
        (self.repo / "code.py").write_text("initial = 1\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "Initial")

    def test_commits_exactly_verified_explicit_file(self):
        (self.repo / "code.py").write_text("updated = 2\n")
        revision = AUTOCOMMIT.commit(self.repo, REPO, ["code.py"], ["tests/test_ok.py"], "Update code")
        self.assertEqual(revision, git(self.repo, "rev-parse", "HEAD"))
        self.assertEqual(git(self.repo, "show", "--pretty=format:", "--name-only", "HEAD"), "code.py")

    def test_refuses_other_changes_and_does_not_stage_anything(self):
        (self.repo / "code.py").write_text("updated = 2\n")
        (self.repo / "other.py").write_text("unrelated = 3\n")
        with self.assertRaisesRegex(ValueError, "Other modified/untracked"):
            AUTOCOMMIT.commit(self.repo, REPO, ["code.py"], ["tests/test_ok.py"], "Update code")
        self.assertEqual(git(self.repo, "diff", "--cached", "--name-only"), "")

    def test_refuses_upstream_and_sensitive_paths(self):
        (self.repo / ".env").write_text("TOP_SECRET=do-not-stage\n")
        with self.assertRaisesRegex(ValueError, "Sensitive or generated"):
            AUTOCOMMIT.commit(self.repo, REPO, [".env"], ["tests/test_ok.py"], "Unsafe")
        with self.assertRaisesRegex(ValueError, "separately owned"):
            AUTOCOMMIT.commit(self.repo, "NousResearch/hermes-agent", ["code.py"], ["tests/test_ok.py"], "Unsafe")


if __name__ == "__main__":
    unittest.main()
