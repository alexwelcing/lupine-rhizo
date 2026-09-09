#!/usr/bin/env python3
"""Regression tests for check_claims.py comment-strip and retire-phrase enforcement.

Runs check_claims.py against disposable mutated copies of the claim-frozen
manuscript (the committed manuscript.tex is never modified):

  (a) an asserting sentence containing an escaped "98\\% systematic error"
      must exit 1 and name the phrase in the diagnostic;
  (a2) the same for an asserting "72.4\\%" (the other %-containing retire
      entry that the old strip made unmatchable);
  (b) the unmodified manuscript — including the retirement-context sentence
      around manuscript.tex:133 — must still exit 0.

Stdlib only; runs standalone (python3 test_check_claims.py) or under pytest.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = ("check_claims.py", "manuscript.tex", "results.json")

ASSERTING_SENTENCES = {
    "98\\% systematic error": "Our analysis confirms 98\\% systematic error across the corpus.",
    "72.4\\%": "The pipeline achieves 72.4\\% fewer DFT evaluations in production.",
}


def run_check(workdir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(workdir / "check_claims.py")],
        capture_output=True,
        text=True,
    )


class CommentStripRegression(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="check-claims-test-")
        self.workdir = Path(self._tmp.name)
        for name in FILES:
            shutil.copy2(HERE / name, self.workdir / name)
        self.manuscript = self.workdir / "manuscript.tex"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def mutate_manuscript(self, sentence: str) -> None:
        text = self.manuscript.read_text(encoding="utf-8")
        assert "\\end{document}" in text, "manuscript lost \\end{document}"
        self.manuscript.write_text(
            text.replace("\\end{document}", sentence + "\n\n\\end{document}"),
            encoding="utf-8",
        )

    def test_asserting_percent_phrases_exit_1_with_diagnostic(self) -> None:
        for phrase, sentence in ASSERTING_SENTENCES.items():
            with self.subTest(phrase=phrase):
                self.mutate_manuscript(sentence)
                proc = run_check(self.workdir)
                self.assertEqual(proc.returncode, 1,
                                 f"asserting {phrase!r} must fail:\n{proc.stdout}{proc.stderr}")
                self.assertIn(phrase, proc.stdout + proc.stderr,
                              f"diagnostic must name the phrase {phrase!r}")

    def test_unmodified_manuscript_exits_0(self) -> None:
        proc = run_check(self.workdir)
        self.assertEqual(proc.returncode, 0,
                         f"clean manuscript must pass:\n{proc.stdout}{proc.stderr}")
        # The retirement-context sentence (manuscript.tex:133 area) must be
        # recognized as retired, not flagged.
        self.assertIn("claim lock OK", proc.stdout)


if __name__ == "__main__":
    unittest.main()
