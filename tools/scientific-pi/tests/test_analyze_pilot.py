"""Real tracked-data join checks; no remote calls, model inference or writes."""
import copy
import importlib.util
from pathlib import Path
import unittest

DIRECTORY = Path(__file__).resolve().parents[1]
ROOT = DIRECTORY.parents[1]
spec = importlib.util.spec_from_file_location("analyze_pilot", DIRECTORY / "analyze_pilot.py")
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


class RealPilotTests(unittest.TestCase):
    def setUp(self):
        self.fixture = pilot.read_input(ROOT, pilot.GEOMETRY)[0]
        self.payloads = {m: pilot.read_input(ROOT, p)[0] for m, p in pilot.BASELINES.items()}

    def test_join_uses_exact_structure_identity_not_array_order(self):
        self.payloads["chgnet"]["predictions"].reverse()
        cases, joined = pilot.validate_join(self.fixture, self.payloads)
        self.assertEqual([len(c["symbols"]) for c in cases], [12, 8, 11, 36, 40])
        first = cases[0]
        # This material ID intentionally differs from the task ID in the name.
        self.assertEqual(first["material_id"], "mp-20974")
        self.assertEqual(joined["chgnet"][first["structure_id"]]["material_id"], first["material_id"])

    def test_missing_or_duplicate_configuration_fails_closed(self):
        for duplicate in (False, True):
            data = copy.deepcopy(self.payloads)
            if duplicate:
                data["chgnet"]["predictions"][-1] = data["chgnet"]["predictions"][0]
            else:
                data["chgnet"]["predictions"].pop()
            with self.subTest(duplicate=duplicate), self.assertRaisesRegex(ValueError, "structure_id"):
                pilot.validate_join(self.fixture, data)

    def test_reference_or_atom_order_drift_is_rejected(self):
        for kind in ("symbols", "reference"):
            data = copy.deepcopy(self.payloads)
            row = data["chgnet"]["predictions"][0]
            if kind == "symbols":
                row["symbols"] = list(reversed(row["symbols"]))
                self.assertNotEqual(row["symbols"], self.fixture["row_fixtures"]["forces"]["structures"][0]["symbols"])
            else:
                row["reference"]["forces_ev_per_angstrom"][0][0] += 0.01
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "ordered symbols or reference"):
                pilot.validate_join(self.fixture, data)

    def test_invalid_values_and_different_contract_are_rejected(self):
        for kind in ("nan", "shape", "contract"):
            data = copy.deepcopy(self.payloads)
            if kind == "contract":
                data["chgnet"]["fixture_contract"]["manifest_hash"] = "different"
            elif kind == "shape":
                data["chgnet"]["predictions"][0]["forces_ev_per_angstrom"][0].pop()
            else:
                data["chgnet"]["predictions"][0]["forces_ev_per_angstrom"][0][0] = float("nan")
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                pilot.validate_join(self.fixture, data)

    def test_actual_alignment_reproduces_archived_method_and_preserves_all_rows(self):
        result = pilot.analyze(ROOT)
        self.assertEqual(result["dataset"], {"configurations": 5, "materials": 5, "atoms": 107, "frames_per_material": 1})
        self.assertEqual(len(result["rows"]), 5)
        for pair in result["pairwise_summary"].values():
            self.assertAlmostEqual(pair["pooled_global_scalar_centered_cosine"],
                                   pair["prior_a6_reported_scalar_centered_cosine"], places=13)
        # Different aggregation functions reverse rank; equal-material squared
        # loss retains the ensemble advantage, so atom weighting alone is not it.
        comparison = result["uniform_ensemble_comparisons"]["sevennet"]
        self.assertLess(comparison["pooled_rmse_ratio_uniform_over_model"], 1)
        self.assertGreater(comparison["material_balanced_rmse_ratio_uniform_over_model"], 1)
        self.assertLess(comparison["material_balanced_root_mean_mse_ratio_uniform_over_model"], 1)
        self.assertEqual(comparison["materials_uniform_beats_model"], 1)


if __name__ == "__main__":
    unittest.main()
