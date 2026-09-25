"""Commit verified Tino changes without staging unrelated files or secrets.

Only an explicitly named set of files in a separately owned Tino GitHub repo
may be committed. `--push` is opt-in; no background git writes are installed.
"""

import argparse
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import time


SENSITIVE = re.compile(r"(^|/)(\.env(?:\..*)?|auth\.json|credentials?[^/]*|.*(?:secret|token|password|private)[^/]*|id_rsa|\.tino-runtime)(/|$)|\.(?:pem|p12|pfx|key)$", re.I)
GENERATED = {".git", ".venv", "venv", "node_modules", "dist", "build", ".hermes", ".tino-runtime"}


def run(repo: Path, *args: str) -> str:
    return subprocess.run(args, cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def validate_file(repo: Path, name: str) -> None:
    path = PurePosixPath(name)
    if path.is_absolute() or not name or str(path) != name or ".." in path.parts or "." in path.parts:
        raise ValueError(f"Invalid file path: {name}")
    if SENSITIVE.search(name) or any(part in GENERATED for part in path.parts):
        raise ValueError(f"Sensitive or generated path is not eligible for automatic commit: {name}")
    candidate = repo / name
    if candidate.is_symlink() or not candidate.is_file() or not candidate.resolve().is_relative_to(repo.resolve()):
        raise ValueError(f"Only regular, existing files within the repository are allowed: {name}")
    if candidate.stat().st_size > 2 * 1024 * 1024:
        raise ValueError(f"File exceeds the 2 MiB automatic commit limit: {name}")


def git_files(repo: Path, *args: str) -> set[str]:
    output = subprocess.run(["git", *args, "-z"], cwd=repo, check=True, capture_output=True).stdout
    return {os.fsdecode(name) for name in output.split(b"\0") if name}


def push_commit(repo: Path, branch: str) -> None:
    """Retry one transient push failure; the operation is non-forcing and idempotent."""
    command = ("git", "push", "origin", f"HEAD:refs/heads/{branch}")
    for attempt in range(2):
        try:
            run(repo, *command)
            return
        except subprocess.CalledProcessError:
            if attempt:
                raise
            time.sleep(1)


def commit(repo: Path, repository: str, paths: list[str], tests: list[str], message: str, push: bool = False) -> str:
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository) or repository.lower() == "nousresearch/hermes-agent":
        raise ValueError("Specify a separately owned Tino GitHub repository (owner/name)")
    repo = repo.resolve()
    if run(repo, "git", "rev-parse", "--show-toplevel") != str(repo):
        raise ValueError("--repo must be the root of the dedicated Tino checkout")
    origin = run(repo, "git", "remote", "get-url", "origin")
    allowed = (f"https://github.com/{repository}.git", f"https://github.com/{repository}", f"git@github.com:{repository}.git")
    if origin.lower() not in tuple(url.lower() for url in allowed):
        raise ValueError("Git origin does not match the explicitly selected Tino repository")
    if not paths or not tests or not message.strip():
        raise ValueError("Explicit --path, --test-path, and --message are required")
    for name in paths:
        validate_file(repo, name)
    for name in tests:
        if not name.startswith("tests/") or not name.endswith(".py"):
            raise ValueError("--test-path must be a Python test file under tests/")
        validate_file(repo, name)
    selected = set(paths)
    if git_files(repo, "diff", "--cached", "--name-only"):
        raise ValueError("The Git index already has staged changes; refusing to include them")
    def changed() -> set[str]:
        tracked = git_files(repo, "diff", "--name-only")
        untracked = git_files(repo, "ls-files", "--others", "--exclude-standard")
        return tracked | untracked
    pending = changed()
    if not pending or not pending <= selected:
        raise ValueError("Other modified/untracked files exist, or selected files have no changes")
    run(repo, str(repo / "scripts" / "run_tests.sh"), *tests)
    if changed() != pending:
        raise ValueError("Working tree changed during tests; refusing to commit")
    run(repo, "git", "diff", "--check", "--", *paths)
    run(repo, "git", "add", "--", *paths)
    try:
        if git_files(repo, "diff", "--cached", "--name-only") != pending:
            raise ValueError("Staged file set changed unexpectedly")
        run(repo, "git", "commit", "-m", message)
    except BaseException:
        run(repo, "git", "reset", "--", *paths)
        raise
    revision = run(repo, "git", "rev-parse", "HEAD")
    if push:
        branch = run(repo, "git", "symbolic-ref", "--short", "HEAD")
        push_commit(repo, branch)
    return revision


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--repository", required=True, help="Explicit Tino GitHub owner/name")
    parser.add_argument("--path", action="append", required=True, help="A single changed file; repeat per file")
    parser.add_argument("--test-path", action="append", required=True, help="A tests/*.py file; repeat per file")
    parser.add_argument("--message", required=True)
    parser.add_argument("--push", action="store_true", help="Also push this commit; never force-push")
    args = parser.parse_args()
    try:
        print(commit(args.repo, args.repository, args.path, args.test_path, args.message, args.push))
        return 0
    except subprocess.CalledProcessError as error:
        print(f"Tino auto-commit stopped: command exited {error.returncode}.", file=sys.stderr)
        if isinstance(error.cmd, (tuple, list)) and tuple(error.cmd[:2]) == ("git", "push"):
            print("The local commit was kept. After checking Git access, retry with `git push origin HEAD`.", file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        print(f"Tino auto-commit stopped: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
