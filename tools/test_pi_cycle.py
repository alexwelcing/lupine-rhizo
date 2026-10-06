"""Offline controller provenance fixtures; no model, CLI, or network execution."""
from contextlib import closing, redirect_stdout
import importlib.util
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import shlex
import sys
import tempfile
import unittest
from unittest import mock

TOOLS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("pi_cycle", TOOLS / "pi-cycle.py")
cycle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cycle)


class ControllerProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.state = Path(self.temporary.name)
        self.brief = {"question": "Fixture research question", "context": "Original evidence packet"}
        self.job = cycle.runner.checked_job({
            "job_id": "saved-discovery", "campaign_id": "original-cycle",
            "machine_id": "homebase-command-center", "provider": "codex",
            "role": "proposer", "tool_mode": "web", **self.brief,
        })
        self.result = json.loads((TOOLS / "scientific-pi/tests/fixtures/proposal.json").read_text())
        self.receipt = {
            "job_id": self.job["job_id"], "job_sha256": cycle.runner.digest(self.job),
            "provider": "codex", "role": "proposer", "status": "completed",
            "completion_unknown": False, "model_execution_started": True,
            "automatic_retry": False, "session_id": "fictional-session",
            "result_sha256": cycle.runner.digest(self.result),
        }
        self.folder = self.state / self.job["job_id"]
        self.folder.mkdir()
        self.write("manifest.json", {"job": self.job, "job_sha256": cycle.runner.digest(self.job)})
        self.write("receipt.json", self.receipt)
        self.write("result.json", self.result)

    def write(self, name, payload):
        (self.folder / name).write_text(json.dumps(payload))

    def test_matching_saved_discovery_is_reusable_without_execution(self):
        with mock.patch.object(cycle.runner, "run_job") as run, mock.patch.object(cycle, "remote_critique") as remote:
            cycle.validate_adopted_discovery(self.state, self.job["job_id"], self.brief)
            receipt, result = cycle.read_completed(self.state, self.job["job_id"])
        self.assertEqual(result, self.result)
        self.assertEqual(receipt["session_id"], "fictional-session")
        run.assert_not_called()
        remote.assert_not_called()

    def test_changed_evidence_stops_before_cycle_creation_or_execution(self):
        with mock.patch.object(cycle.runner, "run_job") as run, mock.patch.object(cycle, "remote_critique") as remote:
            with self.assertRaisesRegex(RuntimeError, "does not match this brief"):
                cycle.run_cycle({**self.brief, "context": "Changed evidence"}, self.state,
                                "new-cycle", self.job["job_id"])
        self.assertFalse((self.state / "new-cycle-cycle").exists())
        run.assert_not_called()
        remote.assert_not_called()

    def test_receipt_for_different_job_or_provider_is_rejected(self):
        for change in ({"job_id": "another-job"}, {"job_sha256": "0" * 64},
                       {"provider": "claude"}, {"role": "critic"}):
            with self.subTest(change=change):
                self.write("receipt.json", {**self.receipt, **change})
                with self.assertRaisesRegex(RuntimeError, "does not match the job manifest"):
                    cycle.read_completed(self.state, self.job["job_id"])

    def test_tampered_manifest_and_self_hashed_invalid_science_are_rejected(self):
        self.write("manifest.json", {"job": {**self.job, "context": "Tampered"},
                                     "job_sha256": cycle.runner.digest(self.job)})
        with self.assertRaisesRegex(RuntimeError, "manifest job identity or hash"):
            cycle.read_completed(self.state, self.job["job_id"])
        self.write("manifest.json", {"job": self.job, "job_sha256": cycle.runner.digest(self.job)})
        self.result["proposals"][0]["cheap_discriminating_experiment"]["execution"] = "completed"
        self.write("result.json", self.result)
        self.write("receipt.json", {**self.receipt, "result_sha256": cycle.runner.digest(self.result)})
        with self.assertRaises(cycle.runner.Invalid):
            cycle.read_completed(self.state, self.job["job_id"])

    def test_unknown_or_unstarted_completion_is_never_adopted(self):
        for change in ({"completion_unknown": True}, {"completion_unknown": None},
                       {"model_execution_started": False}, {"session_id": None},
                       {"automatic_retry": True}, {"status": "timeout"}):
            with self.subTest(change=change):
                self.write("receipt.json", {**self.receipt, **change})
                with self.assertRaisesRegex(RuntimeError, "did not complete"):
                    cycle.validate_adopted_discovery(self.state, self.job["job_id"], self.brief)

    def test_adoption_rejects_path_traversal_and_foreign_role(self):
        with self.assertRaises(ValueError):
            cycle.read_completed(self.state, "../saved-discovery")
        self.job["machine_id"] = "different-machine"
        self.write("manifest.json", {"job": self.job, "job_sha256": cycle.runner.digest(self.job)})
        with self.assertRaisesRegex(RuntimeError, "does not match this brief"):
            cycle.validate_adopted_discovery(self.state, self.job["job_id"], self.brief)

    def save_failed_fixture(self, raw, state, status="timeout", foreign=False):
        job = cycle.runner.checked_job(raw)
        folder = state / job["job_id"]
        folder.mkdir()
        receipt = {
            "job_id": job["job_id"], "job_sha256": cycle.runner.digest(job),
            "provider": job["provider"], "role": job["role"], "status": status,
            "completion_unknown": status == "timeout", "automatic_retry": False,
            "model_execution_started": status != "blocked", "session_id": None,
        }
        if foreign:
            receipt["job_sha256"] = "0" * 64
        cycle.runner.write_json(folder / "manifest.json", {"job": job, "job_sha256": cycle.runner.digest(job)})
        cycle.runner.write_json(folder / "receipt.json", receipt)
        # Even a leftover scientific packet must never become a failure result.
        cycle.runner.write_json(folder / "result.json", self.result)
        return receipt

    def test_critique_timeout_is_durable_null_and_never_starts_decision(self):
        with mock.patch.object(cycle, "remote_critique", side_effect=self.save_failed_fixture) as remote, \
                mock.patch.object(cycle.runner, "run_job") as run, mock.patch.object(cycle, "emit") as emit:
            with self.assertRaisesRegex(RuntimeError, "did not complete"):
                cycle.run_cycle(self.brief, self.state, "timeout-cycle", self.job["job_id"])
        remote.assert_called_once()
        run.assert_not_called()
        with closing(sqlite3.connect(self.state / "pi-ledger.sqlite3")) as db:
            stages = db.execute("SELECT stage,receipt_json,result_json FROM scientific_pi_stages ORDER BY rowid").fetchall()
            status, decision = db.execute("SELECT status,decision_json FROM scientific_pi_cycles").fetchone()
        self.assertEqual([row[0] for row in stages], ["discovery", "independent_critique"])
        self.assertEqual(json.loads(stages[1][1])["status"], "timeout")
        self.assertTrue(json.loads(stages[1][1])["completion_unknown"])
        self.assertEqual(stages[1][2], "null")
        self.assertEqual((status, decision), ("stopped", None))
        self.assertEqual(emit.call_args_list[-1].args[0]["status"], "timeout")
        self.assertFalse((self.state / "timeout-cycle-decision").exists())

    def test_legacy_stage_migration_preserves_history_and_reuses_completed_evidence(self):
        path = self.state / "pi-ledger.sqlite3"
        original = ("prior-cycle", "discovery", self.job["job_id"], json.dumps(self.receipt), json.dumps(self.result))
        with closing(sqlite3.connect(path)) as db:
            db.execute("""CREATE TABLE scientific_pi_stages(cycle_id TEXT NOT NULL, stage TEXT NOT NULL,
                job_id TEXT NOT NULL UNIQUE, receipt_json TEXT NOT NULL, result_json TEXT NOT NULL,
                PRIMARY KEY(cycle_id,stage))""")
            db.execute("INSERT INTO scientific_pi_stages VALUES(?,?,?,?,?)", original)
            db.commit()
        with mock.patch.object(cycle, "remote_critique", side_effect=self.save_failed_fixture) as remote, \
                mock.patch.object(cycle.runner, "run_job") as run, mock.patch.object(cycle, "emit"):
            with self.assertRaisesRegex(RuntimeError, "did not complete"):
                cycle.run_cycle(self.brief, self.state, "explicit-new-cycle", self.job["job_id"])
        run.assert_not_called(); remote.assert_called_once()
        with closing(sqlite3.connect(path)) as db:
            self.assertEqual(db.execute("SELECT * FROM scientific_pi_stages WHERE cycle_id='prior-cycle'").fetchone(), original)
            self.assertEqual(db.execute("SELECT count(*) FROM scientific_pi_stages WHERE job_id=?", (self.job["job_id"],)).fetchone()[0], 2)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO scientific_pi_stages VALUES(?,?,?,?,?)", original)
        backup = path.with_name("pi-ledger.before-stage-sharing.sqlite3")
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        with closing(sqlite3.connect(backup)) as db:
            self.assertEqual(db.execute("SELECT * FROM scientific_pi_stages").fetchall(), [original])
        with closing(cycle.open_ledger(path)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM scientific_pi_stages").fetchone()[0], 3)

    def test_blocked_discovery_is_durable_and_does_not_dispatch_critique(self):
        def blocked(raw, state, _cli):
            return self.save_failed_fixture(raw, state, "blocked")
        with mock.patch.object(cycle.runner, "run_job", side_effect=blocked) as run, \
                mock.patch.object(cycle, "remote_critique") as remote, mock.patch.object(cycle, "emit"):
            with self.assertRaisesRegex(RuntimeError, "did not complete"):
                cycle.run_cycle(self.brief, self.state, "blocked-cycle")
        run.assert_called_once()
        remote.assert_not_called()
        with closing(sqlite3.connect(self.state / "pi-ledger.sqlite3")) as db:
            stage, receipt_json, result_json = db.execute(
                "SELECT stage,receipt_json,result_json FROM scientific_pi_stages").fetchone()
        self.assertEqual(stage, "discovery")
        self.assertEqual(json.loads(receipt_json)["status"], "blocked")
        self.assertEqual(result_json, "null")

    def test_foreign_failure_receipt_is_not_entered_in_stage_ledger(self):
        def foreign(raw, state, _cli):
            return self.save_failed_fixture(raw, state, foreign=True)
        with mock.patch.object(cycle.runner, "run_job", side_effect=foreign), \
                mock.patch.object(cycle, "remote_critique") as remote:
            with self.assertRaisesRegex(RuntimeError, "does not match the job manifest"):
                cycle.run_cycle(self.brief, self.state, "foreign-cycle")
        remote.assert_not_called()
        with closing(sqlite3.connect(self.state / "pi-ledger.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM scientific_pi_stages").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT status FROM scientific_pi_cycles").fetchone()[0], "stopped")


    def test_unknown_remote_launch_is_saved_as_a_noncompleted_stage(self):
        failed = {"returncode": 1, "stop_reason": "timeout", "stdout": b"", "stderr": b""}
        with mock.patch.object(cycle.runner, "bounded_process", return_value=failed) as process, \
                mock.patch.object(cycle.runner, "run_job") as run, mock.patch.object(cycle, "emit"), \
                mock.patch.object(cycle, "remote_command", wraps=cycle.remote_command) as commands:
            with self.assertRaisesRegex(RuntimeError, "did not complete"):
                cycle.run_cycle(self.brief, self.state, "async-unknown", self.job["job_id"])
        process.assert_called_once(); run.assert_not_called()
        self.assertEqual(commands.call_args.args[0]["timeout_seconds"], 300)
        with closing(sqlite3.connect(self.state / "pi-ledger.sqlite3")) as db:
            rows = db.execute("SELECT stage,receipt_json,result_json FROM scientific_pi_stages ORDER BY rowid").fetchall()
        self.assertEqual([row[0] for row in rows], ["discovery", "independent_critique"])
        self.assertEqual(json.loads(rows[1][1])["status"], "launch_unknown")
        self.assertEqual(rows[1][2], "null")


class AsynchronousCritiqueTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.state = Path(self.temporary.name)
        proposal = json.loads((TOOLS / "scientific-pi/tests/fixtures/proposal.json").read_text())
        self.job = cycle.runner.checked_job({
            "job_id": "future-critique", "campaign_id": "future-cycle", "machine_id": "aledev",
            "provider": "claude", "role": "critic", "tool_mode": "none", "timeout_seconds": 300,
            "question": "Fixture research question", "context": "Original evidence packet",
            "review_of": {"job_id": "source-discovery", "packet_sha256": cycle.runner.digest(proposal), "packet": proposal},
        })
        self.result = json.loads((TOOLS / "scientific-pi/tests/fixtures/critique.json").read_text())
        self.result.update(reviewed_job_id="source-discovery", reviewed_packet_sha256=cycle.runner.digest(proposal))
        self.launch = {"job_id": self.job["job_id"], "job_sha256": cycle.runner.digest(self.job), "status": "launched",
                       "worker_pid": 1234, "launch_id": "00000000-1111-4111-8111-111122223333", "automatic_retry": False}
        self.receipt = {"job_id": self.job["job_id"], "job_sha256": cycle.runner.digest(self.job), "provider": "claude",
                        "role": "critic", "status": "completed", "completion_unknown": False,
                        "model_execution_started": True, "automatic_retry": False, "session_id": "fake-session",
                        "returncode": 0, "stop_reason": None, "result_sha256": cycle.runner.digest(self.result)}
        self.clock = [0.0]

    def pending(self):
        return {"job_id": self.job["job_id"], "status": "pending", "completion_unknown": True,
                "receipt": None, "result": None, "launch": self.launch}

    def completed(self):
        return {"job_id": self.job["job_id"], "status": "completed", "completion_unknown": False,
                "receipt": self.receipt, "result": self.result, "launch": self.launch}

    def response(self, action, value, **changes):
        envelope = {"action": action, "job_id": self.job["job_id"], "job_sha256": cycle.runner.digest(self.job),
                    "source_sha256": hashlib.sha256(cycle.RUNNER_SOURCE.encode()).hexdigest(), "value": value, **changes}
        transport = {"exit_code": 0, "timed_out": False, "output_truncated": False, "stdout": json.dumps(envelope)}
        return {"returncode": 0, "stop_reason": None, "stdout": json.dumps(transport).encode(), "stderr": b""}

    def fake_time(self):
        def sleep(seconds):
            self.clock[0] += seconds
        return mock.patch.object(cycle.time, "monotonic", side_effect=lambda: self.clock[0]), mock.patch.object(cycle.time, "sleep", side_effect=sleep)

    def run_remote(self, responses):
        monotonic, sleep = self.fake_time()
        with monotonic, sleep, mock.patch.object(cycle.runner, "bounded_process", side_effect=responses) as process, \
                mock.patch.object(cycle, "remote_command", wraps=cycle.remote_command) as command:
            receipt = cycle.remote_critique(self.job, self.state)
        return receipt, process, command

    def test_one_launch_multiple_status_same_job_source_and_exact_completed_receipt(self):
        receipt, process, command = self.run_remote([
            self.response("launch", self.launch), self.response("status", self.pending()),
            self.response("status", self.pending()), self.response("status", self.completed()),
        ])
        self.assertEqual(receipt, self.receipt)
        self.assertEqual([call.args[2] for call in command.call_args_list], ["launch", "status", "status", "status"])
        for call in command.call_args_list:
            self.assertEqual(call.args[0], self.job)
            self.assertEqual(call.args[1], cycle.RUNNER_SOURCE)
        for call in process.call_args_list:
            self.assertEqual(call.args[0][:3], [cycle.HOMEBASE, "exec", "linux-laptop"])
            self.assertLessEqual(call.args[4], 25)
        self.assertEqual(cycle.read_completed(self.state, self.job["job_id"]), (self.receipt, self.result))
        manifest = json.loads((self.state / self.job["job_id"] / "manifest.json").read_text())
        self.assertTrue(manifest["remote_launch_intent"])
        self.assertEqual(manifest["runner_source_sha256"], hashlib.sha256(cycle.RUNNER_SOURCE.encode()).hexdigest())
        with mock.patch.object(cycle.runner, "bounded_process") as again:
            with self.assertRaises(FileExistsError):
                cycle.remote_critique(self.job, self.state)
        again.assert_not_called()

    def test_launch_transport_failure_preserves_unknown_and_does_not_poll_or_relaunch(self):
        failed = {"returncode": 1, "stop_reason": "timeout", "stdout": b"", "stderr": b"not persisted"}
        receipt, process, command = self.run_remote([failed])
        self.assertEqual(receipt["status"], "launch_unknown")
        self.assertTrue(receipt["completion_unknown"])
        self.assertEqual(receipt["receipt_origin"], "controller_transport")
        self.assertEqual(process.call_count, 1)
        self.assertEqual([call.args[2] for call in command.call_args_list], ["launch"])
        self.assertFalse((self.state / self.job["job_id"] / "result.json").exists())

    def test_oversized_handoff_is_rejected_locally_without_any_transport(self):
        with mock.patch.object(cycle, "REMOTE_COMMAND_CHAR_LIMIT", 20), \
                mock.patch.object(cycle.runner, "bounded_process") as process:
            receipt = cycle.remote_critique(self.job, self.state)
        process.assert_not_called()
        self.assertEqual(receipt["status"], "launch_failed")
        self.assertFalse(receipt["completion_unknown"])
        self.assertFalse(receipt["model_execution_started"])

    def test_uncertain_launch_acknowledgment_does_not_even_poll(self):
        receipt, process, command = self.run_remote([self.response("launch", {**self.launch, "status": "launch_unknown"})])
        self.assertEqual(receipt["status"], "launch_unknown")
        self.assertEqual(process.call_count, 1)
        self.assertEqual(command.call_count, 1)
        self.assertEqual(self.clock[0], 0)

    def test_status_transport_failure_stops_same_job_without_replaying_launch(self):
        failed = {"returncode": 1, "stop_reason": None, "stdout": b"", "stderr": b""}
        receipt, process, command = self.run_remote([self.response("launch", self.launch), failed])
        self.assertEqual(receipt["status"], "status_unknown")
        self.assertTrue(receipt["launch_acknowledged"])
        self.assertEqual(process.call_count, 2)
        self.assertEqual([call.args[2] for call in command.call_args_list], ["launch", "status"])

    def test_wrong_source_version_or_launch_identity_or_result_hash_never_completes(self):
        cases = [
            self.response("status", self.completed(), source_sha256="0" * 64),
            self.response("status", {**self.completed(), "launch": {**self.launch, "worker_pid": 9876}}),
            self.response("status", {**self.completed(), "receipt": {**self.receipt, "result_sha256": "0" * 64}}),
        ]
        for index, response in enumerate(cases):
            with self.subTest(case=index), tempfile.TemporaryDirectory() as temporary:
                self.state = Path(temporary)
                receipt, process, _ = self.run_remote([self.response("launch", self.launch), response])
                self.assertEqual(receipt["status"], "status_unknown")
                self.assertEqual(process.call_count, 2)
                self.assertFalse((self.state / self.job["job_id"] / "result.json").exists())

    def test_pending_wait_is_bounded_and_never_launches_again(self):
        calls = []
        def responses(*args):
            calls.append(args)
            return self.response("launch", self.launch) if len(calls) == 1 else self.response("status", self.pending())
        with mock.patch.object(cycle, "REMOTE_WAIT_SECONDS", 60):
            receipt, _, command = self.run_remote(responses)
        self.assertEqual(receipt["status"], "poll_timeout")
        self.assertLessEqual(self.clock[0], 60)
        self.assertEqual([call.args[2] for call in command.call_args_list].count("launch"), 1)
        self.assertLessEqual(len(calls), 5)

    def test_status_program_reads_exact_installed_source_without_writes_or_launch(self):
        source = "def read_state(root, job_id):\n return {'job_id':job_id,'status':'pending'}\ndef launch_job(*args):\n raise AssertionError('status must never launch')\n"
        remote_home = self.state / "remote-home"
        root = remote_home / ".local/share/lupine-scientific-pi"
        root.mkdir(parents=True)
        source_path = root / ("runner-" + hashlib.sha256(source.encode()).hexdigest() + ".py")
        source_path.write_text(source)
        command = cycle.remote_command(self.job, source, "status")
        program = shlex.split(command)[2]
        output = io.StringIO()
        before = {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}
        original_bytecode_policy = sys.dont_write_bytecode
        try:
            with mock.patch.object(Path, "home", return_value=remote_home), redirect_stdout(output):
                exec(compile(program, "<reviewed-status-fixture>", "exec"), {})
        finally:
            sys.dont_write_bytecode = original_bytecode_policy
        envelope = json.loads(output.getvalue())
        self.assertEqual(envelope["value"], {"job_id": self.job["job_id"], "status": "pending"})
        self.assertEqual(before, {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()})
        self.assertEqual(list(root.rglob("__pycache__")), [])
        source_path.write_text(source + "# changed")
        with mock.patch.object(Path, "home", return_value=remote_home), redirect_stdout(io.StringIO()):
            try:
                with self.assertRaisesRegex(RuntimeError, "installed source version mismatch"):
                    exec(compile(program, "<reviewed-status-fixture>", "exec"), {})
            finally:
                sys.dont_write_bytecode = original_bytecode_policy


if __name__ == "__main__":
    unittest.main()
