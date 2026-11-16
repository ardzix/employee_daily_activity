import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("clockin_release", Path(__file__).resolve().parents[1] / "release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.sha = "a"*40
        release.save(self.folder / "release.json", {"commit": self.sha, "tests": "passed", "digest": "synthetic-digest"})
        self.cs = {"Image": "old-digest", "Env": ["SECRET_KEY=synthetic", "USE_POSTGRES=True", "POSTGRES_HOST=synthetic",
            "POSTGRES_DB=synthetic", "POSTGRES_USER=synthetic", "POSTGRES_PASSWORD=synthetic"]}
        self.old = {"Spec": {"TaskTemplate": {"ContainerSpec": self.cs}}}

    def docker(self, args, **kwargs):
        if args[:2] == ["docker", "exec"]:
            return "-----BEGIN PUBLIC KEY-----\nsynthetic\n-----END PUBLIC KEY-----"
        return ""

    def test_missing_database_configuration_stops_before_migration_or_rollout(self):
        self.cs["Env"] = ["USE_POSTGRES=True"]
        with patch.object(release, "service", return_value=self.old), patch.object(release, "containers", return_value=["old"]), \
             patch.object(release, "run") as run:
            with self.assertRaisesRegex(RuntimeError, "incomplete"):
                release.roll(self.sha, self.folder)
        run.assert_not_called()

    def test_migration_failure_never_updates_the_existing_service(self):
        with patch.object(release, "service", return_value=self.old), patch.object(release, "containers", return_value=["old"]), \
             patch.object(release, "run", side_effect=self.docker) as run, \
             patch.object(release, "wait_task", side_effect=RuntimeError("migration failed")), patch.object(release.subprocess, "run"):
            with self.assertRaisesRegex(RuntimeError, "migration failed"):
                release.roll(self.sha, self.folder)
        self.assertFalse(any(call.args[0][:3] == ["docker", "service", "update"] for call in run.call_args_list))

    def test_roll_preserves_database_and_exposes_only_the_runtime_pointer(self):
        with patch.object(release, "service", return_value=self.old), patch.object(release, "containers", return_value=["old"]), \
             patch.object(release, "run", side_effect=self.docker) as run, patch.object(release, "wait_task"), \
             patch.object(release, "verify") as verify, patch.object(release.subprocess, "run"):
            release.roll(self.sha, self.folder)
        verify.assert_called_once()
        update = next(call.args[0] for call in run.call_args_list if call.args[0][:3] == ["docker", "service", "update"])
        self.assertIn("CLOCKIN_RUNTIME_SECRET_PATH=/run/secrets/clockin_runtime", update)
        self.assertNotIn("POSTGRES_PASSWORD=synthetic", update)
        self.assertNotIn("SECRET_KEY=synthetic", update)
        config = next(json.loads(call.kwargs["input"]) for call in run.call_args_list
                      if call.args[0][:3] == ["docker", "secret", "create"] and "runtime" in call.args[0][3])
        self.assertEqual(config["POSTGRES_PASSWORD"], "synthetic")
        self.assertEqual(config["DEBUG"], "False")
