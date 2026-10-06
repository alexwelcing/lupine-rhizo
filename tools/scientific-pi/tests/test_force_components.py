"""Exact decomposition fixtures and independent Decimal audit of archived data."""
from decimal import Decimal, localcontext
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

DIRECTORY = Path(__file__).resolve().parents[1]
ROOT = DIRECTORY.parents[1]
sys.path.insert(0, str(DIRECTORY))
try:
    spec = importlib.util.spec_from_file_location("force_components", DIRECTORY / "analyze_force_components.py")
    components = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(components)
finally:
    sys.path.pop(0)

def decimal_audit(root, result):
    """Independent dot-product identities: no calls to production decomposition."""
    with localcontext() as context:
        context.prec = 50
        load = lambda path: json.loads(path.read_text(), parse_float=Decimal, parse_int=Decimal)
        fixture = load(root / components.pilot.GEOMETRY)
        payloads = {m: load(root / p) for m, p in components.pilot.BASELINES.items()}
        errors = []
        cases = fixture["row_fixtures"]["forces"]["structures"]
        for case, row in zip(cases, result["rows"], strict=True):
            if case["structure_id"] != row["structure_id"]:
                raise AssertionError("Independent configuration identity mismatch")
            forces = {m: next(p["forces_ev_per_angstrom"] for p in payloads[m]["predictions"] if p["structure_id"] == case["structure_id"]) for m in components.pilot.MODELS}
            ref = case["reference"]["forces_ev_per_angstrom"]
            forces["uniform_ensemble"] = [[sum((forces[m][i][j] for m in components.pilot.MODELS), Decimal(0)) / Decimal(3) for j in range(3)] for i in range(len(ref))]
            for model, pred in forces.items():
                totals = {k: Decimal(0) for k in components.COMPONENTS}
                cross = refsq = Decimal(0)
                for force, estimate in zip(ref, pred, strict=True):
                    delta = [p - f for p, f in zip(estimate, force, strict=True)]
                    e2 = sum((e * e for e in delta), Decimal(0))
                    f2 = sum((f * f for f in force), Decimal(0))
                    ef = sum((e * f for e, f in zip(delta, force, strict=True)), Decimal(0))
                    totals["total"] += e2
                    if f2:
                        totals["parallel"] += ef * ef / f2
                        totals["transverse"] += e2 - ef * ef / f2
                    else:
                        totals["zero_reference"] += e2
                    cross += ef
                    refsq += f2
                metrics = row["models"][model]
                for key in totals:
                    errors.append(abs(float(totals[key]) - metrics["squared_error"][key]))
                if refsq:
                    errors.append(abs(float(cross / refsq) - metrics["signed_parallel_bias_B"]))
                    coherent = cross * cross / refsq
                    errors.append(abs(float(coherent) - metrics["parallel_detail_squared_error"]["coherent_scale"]))
                    errors.append(abs(float(totals["parallel"] - coherent) - metrics["parallel_detail_squared_error"]["atom_varying_remainder"]))
        return {"precision_decimal_digits": 50, "checked_values": len(errors), "maximum_absolute_difference": max(errors)}


class ForceComponentsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.prior = Path(temporary.name) / "prior.json"
        self.proposal = Path(temporary.name) / "proposal-metadata-fixture.json"
        self.prior.write_text(json.dumps(components.pilot.analyze(ROOT)))
        # A fictional metadata fixture only; all force data remain real tracked inputs.
        self.proposal.write_text(json.dumps({"role": "proposer", "proposals": [{"id": "H1"}]}))

    def test_known_projection_and_zero_reference_use_common_denominator(self):
        value = components.decompose([[3, 4, 0], [0, 0, 2]], [[2, 0, 0], [0, 0, 0]])
        self.assertEqual(value["squared_error"], {"parallel": 1, "transverse": 16, "zero_reference": 4, "total": 21})
        self.assertEqual(value["cartesian_mse"]["total"], 21 / 6)
        self.assertEqual(value["signed_parallel_bias_B"], .5)
        self.assertEqual(value["parallel_detail_squared_error"], {"coherent_scale": 1, "atom_varying_remainder": 0})
        self.assertIsNone(value["atom_rows"][1]["signed_parallel_error_ev_per_angstrom"])

    def test_all_zero_and_near_zero_reference_not_dropped(self):
        zero = components.decompose([[1, 2, 3]], [[0, 0, 0]])
        self.assertIsNone(zero["signed_parallel_bias_B"])
        self.assertEqual(zero["squared_error"]["zero_reference"], 14)
        small = components.decompose([[2e-12, 0, 0]], [[1e-12, 0, 0]])
        self.assertEqual(small["zero_reference_atoms"], 0)
        self.assertEqual(small["signed_parallel_bias_B"], 1)
        with self.assertRaises(ValueError):
            components.decompose([[float("nan"), 0, 0]], [[1, 0, 0]])

    def test_rotation_invariance_and_cancelling_atom_biases(self):
        ref = [[1, 2, 3], [-1, -2, -3]]
        pred = [[2, 3, 1], [-.5, -2, -1]]
        rotate = lambda rows: [[-y, x, z] for x, y, z in rows]
        a, b = components.decompose(pred, ref), components.decompose(rotate(pred), rotate(ref))
        for key in components.COMPONENTS:
            self.assertAlmostEqual(a["squared_error"][key], b["squared_error"][key])
        cancel = components.decompose([[2, 0, 0], [0, 0, 0]], [[1, 0, 0], [1, 0, 0]])
        self.assertEqual(cancel["signed_parallel_bias_B"], 0)
        self.assertEqual(cancel["parallel_detail_squared_error"], {"coherent_scale": 0, "atom_varying_remainder": 2})

    def test_actual_archived_values_match_independent_decimal_projection(self):
        result = components.analyze(ROOT, self.prior, self.proposal)
        audit = decimal_audit(ROOT, result)
        self.assertEqual(audit["checked_values"], 140)
        self.assertLess(audit["maximum_absolute_difference"], 3e-13)
        self.assertEqual(sum(row["zero_reference_atoms"] for row in result["rows"]), 2)
        self.assertEqual(sum(row["atoms"] for row in result["rows"]), 107)
        a = result["mechanism_assessment"]
        self.assertEqual(a["verdict"], "exploratory_rule_passes")
        self.assertEqual(a["coherent_bias_assessment"], "not_supported_coherent_scale_error_worsens")
        self.assertEqual(len(a["parallel_harmed_other_materials"]), 4)
        target = next(row for row in result["rows"] if row["material_id"] == components.TARGET)
        target["zero_reference_atoms"] = target["atoms"]
        self.assertEqual(components.assess(result["rows"])["verdict"], "inconclusive")

    def test_source_hash_and_prior_join_are_enforced(self):
        actual = components.read_json
        def altered_hash(path):
            value, receipt = actual(path)
            if path == self.prior:
                value["inputs"][0]["sha256"] = "0" * 64
            return value, receipt
        with mock.patch.object(components, "read_json", side_effect=altered_hash):
            with self.assertRaisesRegex(ValueError, "fingerprint changed"):
                components.analyze(ROOT, self.prior, self.proposal)
        def altered_order(path):
            value, receipt = actual(path)
            if path == self.prior:
                value["rows"].reverse()
            return value, receipt
        with mock.patch.object(components, "read_json", side_effect=altered_order):
            with self.assertRaisesRegex(ValueError, "configuration order"):
                components.analyze(ROOT, self.prior, self.proposal)

    def test_report_escapes_data_and_preserves_mechanism_caveat(self):
        result = components.analyze(ROOT, self.prior, self.proposal)
        result["rows"][0]["material_id"] = "<script>unsafe</script>"
        report = components.render_report(result)
        self.assertNotIn("<script>", report)
        self.assertIn("&lt;script&gt;", report)
        self.assertIn("coherent force-scale correction is not supported", report)


if __name__ == "__main__":
    unittest.main()
