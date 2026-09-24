"""Opt-in, health-checked image upgrades for the private Tino staging instance.

The deployment remains loopback-only. This never touches source checkouts or
other Docker Compose projects, and never migrates the data volume backwards.
"""

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.request import urlopen


COMPOSE = Path(__file__).with_name("tino-staging.compose.yml")
HEALTH_URL = "http://127.0.0.1:9119/api/health"


def validate_image(image: str, repository: str) -> None:
    """Require an image built by the explicitly selected Tino repository."""
    match = re.fullmatch(r"ghcr\.io/([a-z0-9_.-]+/[a-z0-9_.-]+):stable", image.lower())
    if not match or match.group(1) != repository.lower() or repository.lower() == "nousresearch/hermes-agent":
        raise ValueError("TINO_IMAGE must be ghcr.io/<your-tino-repository>:stable, matching TINO_RELEASE_REPOSITORY")


def docker(*args: str) -> str:
    return subprocess.run(["docker", *args], check=True, text=True, capture_output=True).stdout.strip()


def healthy(timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(HEALTH_URL, timeout=3) as response:
                if response.status == 200 and json.load(response).get("ok") is True:
                    return True
        except (OSError, TimeoutError, ValueError):
            pass
        time.sleep(2)
    return False


def upgrade(image: str, repository: str, *, timeout: float = 90) -> str:
    validate_image(image, repository)
    if not COMPOSE.is_file():
        raise FileNotFoundError(COMPOSE)
    compose = ("compose", "-f", str(COMPOSE))
    # First installation is intentionally manual: rollback requires a known
    # healthy image. A failed pull never affects the running container.
    old = docker("image", "inspect", "--format", "{{.Id}}", image)
    if not healthy(6):
        raise RuntimeError("Existing Tino instance is unhealthy; refusing unattended upgrade")
    docker(*compose, "pull", "agent")
    new = docker("image", "inspect", "--format", "{{.Id}}", image)
    if new == old:
        return "already current"
    try:
        docker(*compose, "up", "-d", "--no-deps", "agent")
        is_healthy = healthy(timeout)
    except subprocess.CalledProcessError:
        is_healthy = False
    if is_healthy:
        return f"upgraded to {new}"
    # Restore only the *image* and this Compose service. The volume and any
    # data schema changes are untouched; operators must back up data separately.
    docker("image", "tag", old, image)
    docker(*compose, "up", "-d", "--no-deps", "--force-recreate", "agent")
    if not healthy(timeout):
        raise RuntimeError("Upgrade and image rollback are unhealthy; inspect Tino logs immediately")
    raise RuntimeError("New image failed health check; restored the previous image")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=90)
    args = parser.parse_args()
    image = os.environ.get("TINO_IMAGE", "")
    repository = os.environ.get("TINO_RELEASE_REPOSITORY", "")
    try:
        validate_image(image, repository)
        if args.timeout < 1:
            raise ValueError("--timeout must be at least one second")
        lock = Path.home() / ".cache" / "tino-agent" / "upgrade.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        with lock.open("w") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            print(upgrade(image, repository, timeout=args.timeout))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Tino upgrade stopped: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
