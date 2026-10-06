"""Fixed-ensemble identities, pinned real-data joins and Decimal verification."""
from decimal import Decimal, localcontext
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

DIRECTORY = Path(__file__).resolve().parents[1]
ROOT = DIRECTORY.parents[1]
sys.path.insert(0, str(DIRECTORY))
try:
    spec = importlib.util.spec_from_file_location("ensemble_ambiguity", DIRECTORY / "analyze_ensemble_ambiguity.py")
    ambiguity = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ambiguity)
finally:
    sys.path.pop(0)


def decimal_audit(root, result):
    """Recompute all Gram entries and both sides using Decimal raw-input reads."""
    differences = []
    with localcontext() as context:
        context.prec = 50
        load = lambda path: json.loads(path.read_text(), parse_float=Decimal)
        fixture = load(root / ambiguity.pilot.GEOMETRY)
        sources = {m: load(root / path) for m, path in ambiguity.pilot.BASELINES.items()}
        for case, row in zip(fixture["row_fixtures"]["forces"]["structures"], result["rows"], strict=True):
            if case["structure_id"] != row["structure_id"]:
                raise AssertionError("Independent join differs")
            ref = [Decimal(v) for atom in case["reference"]["forces_ev_per_angstrom"] for v in atom]
            residuals = []
            for model in ambiguity.pilot.MODELS:
                pred = next(p for p in sources[model]["predictions"] if p["structure_id"] == case["structure_id"])
                force = [Decimal(v) for atom in pred["forces_ev_per_angstrom"] for v in atom]
                residuals.append([p - f for p, f in zip(force, ref, strict=True)])
            dot = lambda a, b: sum((x * y for x, y in zip(a, b, strict=True)), Decimal(0))
            dimensions = Decimal(len(ref))
            gram = [[dot(a, b) / dimensions for b in residuals] for a in residuals]
            mean = [sum((r[i] for r in residuals), Decimal(0)) / Decimal(3) for i in range(len(ref))]
            mean_member = sum((gram[i][i] for i in range(3)), Decimal(0)) / Decimal(3)
            ensemble = dot(mean, mean) / dimensions
            disagreement = sum((dot([e - a for e, a in zip(r, mean, strict=True)], [e - a for e, a in zip(r, mean, strict=True)]) for r in residuals), Decimal(0)) / (Decimal(3) * dimensions)
            if abs(mean_member - disagreement - ensemble) > Decimal("1e-45"):
                raise AssertionError("Independent exact-identity arithmetic failed")
            for i in range(3):
                for j in range(3):
                    differences.append(abs(float(gram[i][j]) - row["metrics"]["residual_gram_mse"][i][j]))
            for key, value in (("mean_member_mse", mean_member), ("disagreement_mse", disagreement), ("ensemble_mse", ensemble)):
                differences.append(abs(float(value) - row["metrics"][key]))
    return {"decimal_precision_digits": 50, "checked_values": len(differences), "maximum_absolute_difference": max(differences)}


class EnsembleAmbiguityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.prior = Path(temporary.name) / "prior-component-fixture.json"
        # Reproduce total errors from tracked inputs without relying on private artifacts in CI.
        previous = ambiguity.pilot.analyze(ROOT)
        for row in previous["rows"]:
            row["models"] = {m: {"cartesian_mse": {"total": values["squared_error_ev2_per_angstrom2"] / (3 * row["atoms"])}} for m, values in row["models"].items()}
        self.prior.write_text(json.dumps(previous))

    def test_opposing_residuals_cancel_and_gram_offdiagonals_are_signed(self):
        predictions = {"chgnet": [[2, 2, 3]], "mace-mp-0": [[0, 2, 3]], "sevennet": [[1, 2, 3]]}
        result = ambiguity.force_ambiguity(predictions, [[1, 2, 3]])
        self.assertEqual(result["residual_gram_sse"], [[1, -1, 0], [-1, 1, 0], [0, 0, 0]])
        self.assertEqual(result["ensemble_mse"], 0)
        self.assertAlmostEqual(result["mean_member_mse"], 2 / 9)
        self.assertAlmostEqual(result["disagreement_mse"], 2 / 9)
        self.assertFalse(result["ensemble_beats_best_member"])
        self.assertIsNone(result["ensemble_rmse_increase_over_best_percent"])

    def test_identical_members_have_zero_disagreement_and_keep_zero_reference_atoms(self):
        predictions = {m: [[1, 2, 0], [0, 0, 0]] for m in ambiguity.pilot.MODELS}
        result = ambiguity.force_ambiguity(predictions, [[0, 0, 0], [0, 0, 0]])
        self.assertEqual(result["disagreement_mse"], 0)
        self.assertAlmostEqual(result["ensemble_mse"], 5 / 6)
        with self.assertRaises(ValueError):
            ambiguity.force_ambiguity({**predictions, "chgnet": [[1, 2, 0]]}, [[0, 0, 0], [0, 0, 0]])

    def test_real_arrays_match_independent_decimal_and_prior_is_immutable(self):
        before = self.prior.read_bytes()
        result = ambiguity.analyze(ROOT, self.prior)
        self.assertEqual(self.prior.read_bytes(), before)
        audit = decimal_audit(ROOT, result)
        self.assertEqual(audit["checked_values"], 60)
        self.assertLess(audit["maximum_absolute_difference"], 1e-14)
        self.assertEqual(result["findings"]["materials_ensemble_beats_retrospective_best"], 0)
        self.assertFalse(result["findings"]["ensemble_beats_chgnet_in_rescue_material"])
        self.assertAlmostEqual(result["findings"]["rescue_ensemble_rmse_increase_over_chgnet_percent"], 6.034604956708778)
        self.assertEqual(result["findings"]["negative_off_diagonal_sum_materials"], ["mp-759876"])
        self.assertTrue(result["pooled"]["ensemble_beats_best_single_member_over_panel"])
        self.assertTrue(result["equal_material"]["ensemble_beats_best_single_member_over_panel"])
        self.assertGreater(result["mean_material_rmse"]["uniform_ensemble"], result["mean_material_rmse"]["sevennet"])

    def test_changed_fingerprint_and_atom_order_fail_closed(self):
        original = json.loads(self.prior.read_text())
        original["inputs"][0]["sha256"] = "0" * 64
        self.prior.write_text(json.dumps(original))
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            ambiguity.analyze(ROOT, self.prior)
        original["inputs"][0]["sha256"] = ambiguity.PINNED_INPUTS[ambiguity.pilot.GEOMETRY]
        original["rows"][0]["ordered_symbols"].reverse()
        self.prior.write_text(json.dumps(original))
        with self.assertRaisesRegex(ValueError, "atom identity"):
            ambiguity.analyze(ROOT, self.prior)

    def test_html_escapes_strings_and_does_not_accept_rejected_critique(self):
        result = ambiguity.analyze(ROOT, self.prior)
        result["rows"][0]["material_id"] = "<script>no</script>"
        report = ambiguity.render_report(result)
        self.assertNotIn("<script>", report)
        self.assertIn("&lt;script&gt;", report)
        self.assertIn("retrospectively", report)
        self.assertIn("rejected Claude packet is context only", report)
        self.assertIn("b8c37e33defde51cf91e1e03e51657da-Paper.pdf", report)


if __name__ == "__main__":
    unittest.main()
