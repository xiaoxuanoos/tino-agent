"""Image upgrades stay scoped to the separately owned Tino staging service."""

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[2] / "deploy" / "tino_auto_upgrade.py"
SPEC = importlib.util.spec_from_file_location("tino_auto_upgrade", SOURCE)
UPGRADER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UPGRADER)
IMAGE = "ghcr.io/tino-owner/tino-agent:stable"
REPO = "tino-owner/tino-agent"


class TinoUpgradeTests(unittest.TestCase):
    def test_never_accepts_upstream_or_mismatched_image(self):
        for image, repo in (
            ("ghcr.io/nousresearch/hermes-agent:stable", "nousresearch/hermes-agent"),
            ("ghcr.io/tino-owner/another:stable", REPO),
            ("docker.io/tino-owner/tino-agent:stable", REPO),
            ("ghcr.io/tino-owner/tino-agent:latest", REPO),
        ):
            with self.subTest(image=image), self.assertRaises(ValueError):
                UPGRADER.validate_image(image, repo)
        UPGRADER.validate_image(IMAGE, REPO)

    @patch.object(UPGRADER, "healthy", side_effect=[True, False, True])
    @patch.object(UPGRADER, "docker")
    def test_failed_upgrade_restores_old_image_and_only_recreates_tino(self, docker, healthy):
        docker.side_effect = ["sha256:old", "", "sha256:new", "", "", ""]
        with self.assertRaisesRegex(RuntimeError, "restored the previous image"):
            UPGRADER.upgrade(IMAGE, REPO, timeout=1)
        self.assertEqual(docker.call_args_list[0].args, ("image", "inspect", "--format", "{{.Id}}", IMAGE))
        self.assertEqual(docker.call_args_list[4].args, ("image", "tag", "sha256:old", IMAGE))
        self.assertEqual(docker.call_args_list[5].args[-5:], ("up", "-d", "--no-deps", "--force-recreate", "agent"))
        self.assertEqual(healthy.call_count, 3)

    @patch.object(UPGRADER, "healthy", return_value=True)
    @patch.object(UPGRADER, "docker")
    def test_equal_image_does_not_restart_running_agent(self, docker, healthy):
        docker.side_effect = ["sha256:same", "", "sha256:same"]
        self.assertEqual(UPGRADER.upgrade(IMAGE, REPO), "already current")
        self.assertEqual(docker.call_count, 3)
        self.assertEqual(healthy.call_count, 1)


if __name__ == "__main__":
    unittest.main()
