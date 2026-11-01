"""The setup/model environment boundary, using mocked child processes only."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("model_execute", Path(__file__).with_name("execute.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExecutionBoundary(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.previous = Path.cwd()
        os.chdir(self.root)
        (self.root / ".lupine-coding-evidence").mkdir()
        self.node = self.root / "node"
        self.node.write_text("synthetic executable identity; never run")
        self.calls = []
        self.raw = json.dumps({"deadlineAtMs": 1900000600000, "capability": "x" * 48})

    def tearDown(self):
        os.chdir(self.previous)
        self.temp.cleanup()

    def child(self, command, **options):
        self.calls.append((command, options))
        if len(self.calls) == 1:
            (self.root / ".lupine-coding-evidence/model-prepared.json").write_text(json.dumps({
                "schema": "lupine.dsh-model-prepared.v1", "targetRoot": str(self.root),
                "nodeExecutable": str(self.node), "nodeVersion": "v22.22.3"}))
        else:
            for name in module.ARTIFACT_NAMES:
                file = self.root / ".lupine-coding-evidence" / name
                if not file.exists():
                    file.write_text('synthetic produced artifact; no subprocess ran')
        return types.SimpleNamespace(returncode=0)

    def run_main(self, child=None, raw=None):
        with patch.dict(os.environ, {"LUPINE_CODING_MODEL_CONFIG_JSON": self.raw if raw is None else raw,
                                     "UNRELATED_TOKEN": "must-not-forward"}, clear=True), \
             patch.object(module.time, "time", return_value=1900000000), \
             patch.object(module.subprocess, "run", side_effect=child or self.child):
            return module.main()

    def test_only_second_phase_receives_scoped_capability(self):
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(set(self.calls[0][1]["env"]), {"PATH"})
        self.assertEqual(self.calls[1][1]["env"]["LUPINE_CODING_MODEL_CONFIG_JSON"], self.raw)
        self.assertNotIn("UNRELATED_TOKEN", self.calls[1][1]["env"])
        self.assertNotIn(self.raw, str(self.calls[0][0]) + str(self.calls[1][0]))
        self.assertLessEqual(self.calls[0][1]["timeout"], 585)
        self.assertLessEqual(self.calls[1][1]["timeout"], 585)

    def test_failed_preparation_never_starts_model(self):
        def fail(command, **options):
            self.calls.append((command, options))
            return types.SimpleNamespace(returncode=1)
        with self.assertRaisesRegex(RuntimeError, "inference not started"):
            self.run_main(fail)
        self.assertEqual(len(self.calls), 1)

    def test_unknown_preparation_never_starts_model(self):
        def timeout(command, **options):
            self.calls.append((command, options))
            raise module.subprocess.TimeoutExpired("fixed setup", options["timeout"])
        with self.assertRaises(module.subprocess.TimeoutExpired):
            self.run_main(timeout)
        self.assertEqual(len(self.calls), 1)

    def test_expired_or_enlarged_window_prevents_all_children(self):
        for deadline in [1900000000000, 1900000900001, True]:
            with self.assertRaises(RuntimeError):
                self.run_main(raw=json.dumps({"deadlineAtMs": deadline}))
        self.assertEqual(self.calls, [])

    def test_bad_prepared_runtime_stops_before_model(self):
        def bad(command, **options):
            result = self.child(command, **options)
            file = self.root / ".lupine-coding-evidence/model-prepared.json"
            value = json.loads(file.read_text()); value["nodeVersion"] = "v22.15.0"; file.write_text(json.dumps(value))
            return result
        with self.assertRaises(RuntimeError):
            self.run_main(bad)
        self.assertEqual(len(self.calls), 1)

    def test_known_model_failure_preserves_exit_and_explicit_absences(self):
        def child(command, **options):
            if not self.calls:
                return self.child(command, **options)
            self.calls.append((command, options))
            file = self.root / '.lupine-coding-evidence/model-runtime-result.json'
            file.write_text('{"outcome":"failed","modelTurns":[]}')
            return types.SimpleNamespace(returncode=1)
        self.assertEqual(self.run_main(child), 1)
        output = self.root / '.lupine-coding-evidence'
        self.assertEqual((output / 'model-runtime-result.json').read_text(), '{"outcome":"failed","modelTurns":[]}')
        absent = json.loads((output / 'repository-assessment.json').read_text())
        self.assertEqual(absent['schema'], 'lupine.coding-artifact-absent.v1')
        self.assertFalse(absent['produced'])
        self.assertEqual(absent['commandExitCode'], 1)
        self.assertIn('not a repository assessment', (output / 'repository-assessment.md').read_text())
        self.assertNotIn('x' * 48, ''.join(p.read_text() for p in output.iterdir()))

    def test_missing_deliverables_cannot_be_success(self):
        def child(command, **options):
            if not self.calls:
                return self.child(command, **options)
            self.calls.append((command, options))
            return types.SimpleNamespace(returncode=0)
        self.assertEqual(self.run_main(child), 1)

    def test_unknown_failure_creates_absence_without_known_exit_claim(self):
        def timeout(command, **options):
            raise module.subprocess.TimeoutExpired('fixed', 1)
        with self.assertRaises(module.subprocess.TimeoutExpired):
            self.run_main(timeout)
        absent = json.loads((self.root / '.lupine-coding-evidence/repository-assessment.json').read_text())
        self.assertIsNone(absent['commandExitCode'])


if __name__ == "__main__":
    unittest.main()
