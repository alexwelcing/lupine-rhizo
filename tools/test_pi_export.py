"""Offline export fixtures; no CLI, model, network or remote device calls."""
from contextlib import closing
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("pi_export", TOOLS / "pi-export.py")
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)
runner = exporter.runner


class ResearchExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name)
        self.packet = json.loads((TOOLS / "scientific-pi/tests/fixtures/proposal.json").read_text())
        self.job = runner.checked_job({"job_id": "fixture-discovery", "campaign_id": "fixture",
            "machine_id": "homebase-command-center", "provider": "codex", "role": "proposer", "tool_mode": "web",
            "question": "Original broad research question", "context": "Synthetic test context"})
        self.receipt = {"job_id": self.job["job_id"], "job_sha256": runner.digest(self.job),
            "provider": "codex", "role": "proposer", "status": "completed", "completion_unknown": False,
            "returncode": 0, "stop_reason": None, "model_execution_started": True, "automatic_retry": False, "session_id": "fixture-session", "model": "fixture-model",
            "started_at": "2026-10-05T10:00:00.000Z", "finished_at": "2026-10-05T10:01:00.000Z",
            "result_sha256": runner.digest(self.packet), "cli": "/Users/private/bin/codex", "raw_output": "secret protocol diagnostics"}
        self.folder = self.state / self.job["job_id"]
        self.folder.mkdir()
        self.write("manifest.json", {"job": self.job, "job_sha256": runner.digest(self.job)})
        self.write("receipt.json", self.receipt)
        self.write("result.json", self.packet)
        with closing(sqlite3.connect(self.state / "pi-ledger.sqlite3")) as db, db:
            db.executescript("""CREATE TABLE scientific_pi_cycles(cycle_id TEXT PRIMARY KEY,question TEXT,started_at TEXT,finished_at TEXT,status TEXT,decision_json TEXT,error TEXT);
                CREATE TABLE scientific_pi_stages(cycle_id TEXT,stage TEXT,job_id TEXT,receipt_json TEXT,result_json TEXT);""")
            db.execute("INSERT INTO scientific_pi_cycles VALUES(?,?,?,?,'stopped',NULL,?)", ("fixture", self.job["question"], "2026-10-05T10:00:00.000Z", "2026-10-05T10:02:00.000Z", "/Users/private/state/failed: secret"))
            db.execute("INSERT INTO scientific_pi_stages VALUES('fixture','discovery',?,?,?)", (self.job["job_id"], json.dumps(self.receipt), json.dumps(self.packet)))

    def write(self, name, value):
        (self.folder / name).write_text(json.dumps(value))

    def test_exports_real_receipt_projection_without_paths_protocol_logs_or_execution_claim(self):
        value = exporter.export_cycle(self.state, "fixture")
        self.assertEqual(value["status"], "stopped")
        self.assertEqual(value["question"], "Original broad research question")
        self.assertEqual(json.loads(value["stages"][0]["packetJson"])["research_question"], "Fixture research question")
        self.assertEqual(value["stages"][0]["receipt"]["resultSha256"], runner.digest(self.packet))
        self.assertEqual(value["stages"][0]["machineId"], "mac")
        self.assertEqual(value["stages"][1]["status"], "not_started")
        self.assertEqual(value["experiment"], "not_started")
        self.assertEqual(value["publication"], "held")
        for private in ("/Users/", "secret", "raw_output", "cli"):
            if private == "cli":
                self.assertNotIn('"cli":', json.dumps(value))
            else:
                self.assertNotIn(private, json.dumps(value))

    def test_refuses_modified_receipt_and_modified_result(self):
        self.write("receipt.json", {**self.receipt, "session_id": "different"})
        with self.assertRaisesRegex(ValueError, "differs"):
            exporter.export_cycle(self.state, "fixture")
        self.write("receipt.json", self.receipt)
        self.write("result.json", {**self.packet, "synthesis": "Changed answer"})
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            exporter.export_cycle(self.state, "fixture")

    def test_checks_job_manifest_and_role(self):
        changed = {**self.job, "machine_id": "unknown-host"}
        self.write("manifest.json", {"job": changed, "job_sha256": runner.digest(changed)})
        with self.assertRaisesRegex(ValueError, "role"):
            exporter.export_cycle(self.state, "fixture")

    def test_manifest_without_receipt_is_pending_not_success(self):
        with closing(sqlite3.connect(self.state / "pi-ledger.sqlite3")) as db, db:
            db.execute("DELETE FROM scientific_pi_stages")
            db.execute("UPDATE scientific_pi_cycles SET status='running',finished_at=NULL,error=NULL")
        (self.folder / "receipt.json").unlink()
        value = exporter.export_cycle(self.state, "fixture")
        stage = value["stages"][0]
        self.assertEqual(stage["status"], "pending")
        self.assertIsNone(stage["packetJson"])
        self.assertIsNone(stage["receipt"])

    def test_failed_receipt_has_no_result_even_if_a_stale_packet_exists(self):
        failed = {**self.receipt, "status": "timeout", "completion_unknown": True}
        self.write("receipt.json", failed)
        with closing(sqlite3.connect(self.state / "pi-ledger.sqlite3")) as db, db:
            db.execute("UPDATE scientific_pi_stages SET receipt_json=?,result_json='null'", (json.dumps(failed),))
        value = exporter.export_cycle(self.state, "fixture")
        self.assertEqual(value["stages"][0]["status"], "timeout")
        self.assertIsNone(value["stages"][0]["packetJson"])
        self.assertIsNone(value["stages"][0]["receipt"]["resultSha256"])

    def test_complete_cycle_requires_all_three_matching_results(self):
        with closing(sqlite3.connect(self.state / "pi-ledger.sqlite3")) as db, db:
            db.execute("UPDATE scientific_pi_cycles SET status='completed',decision_json='{}'")
        with self.assertRaisesRegex(ValueError, "lacks matching"):
            exporter.export_cycle(self.state, "fixture")

    def test_contradictory_completed_process_receipt_is_rejected(self):
        for fields in ({"returncode": 1}, {"stop_reason": "timeout"}):
            receipt = {**self.receipt, **fields}
            self.write("receipt.json", receipt)
            with closing(sqlite3.connect(self.state / "pi-ledger.sqlite3")) as db, db:
                db.execute("UPDATE scientific_pi_stages SET receipt_json=?", (json.dumps(receipt),))
            with self.assertRaisesRegex(ValueError, "cannot prove"):
                exporter.export_cycle(self.state, "fixture")

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO test requires POSIX")
    def test_fifo_cannot_block_the_exporter(self):
        target = self.state / "not-a-file.json"
        os.mkfifo(target)
        with self.assertRaisesRegex(ValueError, "regular file"):
            exporter.read_json(target)

    def test_does_not_create_missing_ledger_or_accept_traversal(self):
        with self.assertRaises(ValueError):
            exporter.export_cycle(self.state, "../fixture")
        with tempfile.TemporaryDirectory() as other:
            with self.assertRaises(sqlite3.OperationalError):
                exporter.export_cycle(Path(other), "fixture")
            self.assertEqual(list(Path(other).iterdir()), [])

    def test_rejects_host_paths_embedded_in_scientific_packet_without_rewriting_hashes(self):
        self.packet["synthesis"] = "Private source /Users/person/research.json"
        self.receipt["result_sha256"] = runner.digest(self.packet)
        self.write("result.json", self.packet); self.write("receipt.json", self.receipt)
        with closing(sqlite3.connect(self.state / "pi-ledger.sqlite3")) as db, db:
            db.execute("UPDATE scientific_pi_stages SET receipt_json=?,result_json=?", (json.dumps(self.receipt), json.dumps(self.packet)))
        with self.assertRaisesRegex(ValueError, "private host path"):
            exporter.export_cycle(self.state, "fixture")


if __name__ == "__main__":
    unittest.main()
