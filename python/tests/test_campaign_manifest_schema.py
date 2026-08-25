"""Acceptance tests for the campaign-manifest v1 JSON Schema."""

from __future__ import annotations

import hashlib
import json
import unittest
from fractions import Fraction
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[2]


def load(relative_path: str) -> dict:
    with (ROOT / relative_path).open(encoding="utf-8") as stream:
        return json.load(stream)


def allocation_exists(capacities: list[int], quota: int, minimum_occupancy: int) -> bool:
    """Exact feasibility for occupancies in {0} union [minimum, capacity]."""
    reachable = {0}
    for capacity in capacities:
        choices = [0, *range(minimum_occupancy, capacity + 1)]
        reachable = {
            subtotal + choice
            for subtotal in reachable
            for choice in choices
            if subtotal + choice <= quota
        }
    return quota in reachable


def structure_level_hull_sign(model_differences: list[int]) -> int:
    """Aggregate exactly four fixed-point model differences with half-even median."""
    if len(model_differences) != 4:
        raise ValueError("all four registered model pairs are required")
    ordered = sorted(model_differences)
    median = round(Fraction(ordered[1] + ordered[2], 2))
    return (median > 0) - (median < 0)


class CampaignManifestSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest_schema = load("schemas/campaign-manifest.v1.schema.json")
        Draft202012Validator.check_schema(cls.manifest_schema)
        cls.manifest_validator = Draft202012Validator(cls.manifest_schema)

    def test_round_4_manifest_with_uma_exclusion_passes(self) -> None:
        manifest = load("examples/campaign-manifest.round-4.v1.json")
        self.manifest_validator.validate(manifest)
        self.assertTrue(
            any(
                exclusion["subject"] == "UMA"
                and exclusion["disposition"] == "deprioritized"
                for exclusion in manifest["exclusions"]
            )
        )

    def test_condition_action_must_match_its_block(self) -> None:
        manifest = load("examples/campaign-manifest.round-4.v1.json")
        manifest["kill_conditions"][0]["action"] = "demote"
        with self.assertRaises(ValidationError):
            self.manifest_validator.validate(manifest)

    def test_recorded_inputs_declare_retrospective_analysis_sources(self) -> None:
        manifest = load(
            "campaigns/v1/literature-protocol-offset-sign-skew.campaign-manifest.v1.json"
        )
        self.manifest_validator.validate(manifest)
        recorded = manifest["preregistration"]["recorded_inputs"]
        self.assertEqual(
            [item["path"] for item in recorded],
            ["data/candidates/z1-union-campaign.json"],
        )

        invalid = load(
            "campaigns/v1/literature-protocol-offset-sign-skew.campaign-manifest.v1.json"
        )
        invalid["preregistration"]["recorded_inputs"] = []
        with self.assertRaises(ValidationError):
            self.manifest_validator.validate(invalid)

    def test_manifest_requires_explicit_exclusions_block(self) -> None:
        manifest = load("examples/campaign-manifest.round-4.v1.json")
        del manifest["exclusions"]
        with self.assertRaises(ValidationError):
            self.manifest_validator.validate(manifest)

    def test_discovery_chain_manifests_are_frozen_and_content_addressed(self) -> None:
        paths = sorted((ROOT / "campaigns" / "v1").glob("*.json"))
        self.assertEqual(
            [path.stem.split(".")[0] for path in paths],
            [
                "correction-round4",
                "correction-round5-optimal-bias-grouping-heldout-v4",
                "correction-round5-optimal-bias-v3",
                "correction-round5-sharp-v2",
                "correction-round5-sharp",
                "literature-protocol-offset-sign-skew",
                "z1",
                "z1r5",
                "z2",
                "z3",
            ],
        )

        for path in paths:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            self.manifest_validator.validate(manifest)
            unhashed = {key: value for key, value in manifest.items() if key != "content_hash"}
            canonical = json.dumps(
                unhashed, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            ).encode("utf-8")
            expected = "sha256:" + hashlib.sha256(canonical).hexdigest()
            self.assertEqual(manifest["content_hash"], expected)
            self.assertTrue(manifest["preregistration"]["frozen_before_execution"])
            self.assertTrue(all(item["frozen"] for item in manifest["frozen_hypotheses"]))
            self.assertTrue(manifest["evidence_requirements"])

    def test_discovery_chain_acceptance_tests_are_exact(self) -> None:
        manifests = {
            path.stem.split(".")[0]: json.loads(path.read_text(encoding="utf-8"))
            for path in (ROOT / "campaigns" / "v1").glob("*.json")
        }
        self.assertEqual(
            manifests["z1"]["acceptance_test"],
            {"metric": "barrier_mae", "operator": "lte", "threshold": 40, "unit": "meV"},
        )
        self.assertEqual(
            manifests["z2"]["acceptance_test"],
            {"metric": "magnetocrystalline_anisotropy_rank_correlation", "operator": "eq", "threshold": 1, "unit": "spearman_rho"},
        )
        self.assertEqual(
            manifests["z3"]["acceptance_test"],
            {"metric": "adsorption_energy_mae", "operator": "lte", "threshold": 0.1, "unit": "eV"},
        )

    def test_exclusions_do_not_block_available_models(self) -> None:
        for path in (ROOT / "campaigns" / "v1").glob("*.json"):
            manifest = json.loads(path.read_text(encoding="utf-8"))
            available = {model["model_id"] for model in manifest["available_models"]}
            excluded = {item["subject"] for item in manifest["exclusions"]}
            self.assertTrue(available)
            self.assertTrue(available.isdisjoint(excluded))
            self.assertFalse(manifest["execution"]["excluded_models_block_execution"])

    def test_round5_sharp_v2_preregistration_is_powered_and_elastic_only(self) -> None:
        manifest = load("campaigns/v1/correction-round5-sharp-v2.campaign-manifest.v1.json")
        panel = load("data/candidates/round5_elastic_panel-selection.v2.lock.json")

        self.manifest_validator.validate(manifest)
        self.assertEqual(panel["unit_definition"]["structures"], 125)
        self.assertEqual(panel["unit_definition"]["models_per_structure"], 4)
        self.assertEqual(panel["unit_definition"]["total_cells"], 500)
        self.assertIn("litraj-neb-path", panel["unit_definition"]["excluded_unit_kinds"])
        self.assertEqual(
            panel["analysis_requirements"][
                "minimum_distinct_non_tied_applied_structures_per_class_property"
            ],
            16,
        )
        self.assertEqual(panel["analysis_requirements"]["primary_alpha"], 0.1)
        self.assertEqual(panel["analysis_requirements"]["secondary_sampling_unit"], "distinct-structure")
        self.assertEqual(
            panel["analysis_requirements"]["secondary_required_registered_model_pairs_per_structure"],
            4,
        )
        self.assertEqual(
            panel["grouping_tuple"],
            [
                "class",
                "chemistry",
                "structure_prototype",
                "composition_space_neighbourhood",
            ],
        )
        self.assertEqual(panel["execution_requirements"]["max_retries"], 0)
        self.assertTrue(panel["execution_requirements"]["immutable_image_digests"])

        allocation = panel["allocation_contract"]
        self.assertEqual(allocation["minimum_selected_occupancy_per_used_grouping_tuple"], 5)
        self.assertEqual(
            allocation["minimum_predispatch_calibration_eligible_structures_per_class_property"],
            16,
        )
        self.assertFalse(allocation["predispatch_power_check_uses_model_outputs"])
        self.assertNotIn("round-robin", " ".join(panel["selection_algorithm"]).lower())

        panel_path = ROOT / manifest["execution"]["candidate_panel"]["path"]
        self.assertEqual(
            manifest["execution"]["candidate_panel"]["sha256"],
            "sha256:" + hashlib.sha256(panel_path.read_bytes()).hexdigest(),
        )

        prereg_path = ROOT / manifest["preregistration"]["input_document"]["path"]
        self.assertEqual(
            manifest["preregistration"]["input_document"]["sha256"],
            "sha256:" + hashlib.sha256(prereg_path.read_bytes()).hexdigest(),
        )

    def test_round5_v2_rejects_adversarial_many_strata_without_complete_groups(self) -> None:
        panel = load("data/candidates/round5_elastic_panel-selection.v2.lock.json")
        minimum = panel["allocation_contract"][
            "minimum_selected_occupancy_per_used_grouping_tuple"
        ]

        # The rejected v1 round-robin could choose one from each of 63 groups.
        # V2 must refuse because 63 cannot be composed from complete size-5 groups.
        self.assertFalse(allocation_exists([5] * 63, 63, minimum))
        self.assertFalse(allocation_exists([5] * 62, 62, minimum))

        # Exact feasible allocations remain admitted without underfilled groups.
        self.assertTrue(allocation_exists([8, *([5] * 11)], 63, minimum))
        self.assertTrue(allocation_exists([7, *([5] * 11)], 62, minimum))

    def test_round5_v2_hull_width_sign_test_does_not_pseudoreplicate_models(self) -> None:
        panel = load("data/candidates/round5_elastic_panel-selection.v2.lock.json")
        self.assertEqual(panel["analysis_requirements"]["secondary_sampling_unit"], "distinct-structure")

        signs = [structure_level_hull_sign([1, 1, 1, 1]) for _ in range(3)]
        self.assertEqual(signs, [1, 1, 1])
        self.assertEqual(Fraction(1, 2 ** len(signs)), Fraction(1, 8))
        self.assertEqual(Fraction(1, 2 ** 12), Fraction(1, 4096))
        self.assertGreater(Fraction(1, 8), Fraction(1, 10))

        self.assertEqual(structure_level_hull_sign([-3, -1, 1, 3]), 0)
        with self.assertRaisesRegex(ValueError, "all four registered model pairs"):
            structure_level_hull_sign([1, 1, 1])

    def test_round5_v3_registers_optimal_estimator_and_robust_gate(self) -> None:
        manifest = load(
            "campaigns/v1/correction-round5-optimal-bias-v3.campaign-manifest.v1.json"
        )
        panel = load("data/candidates/round5_elastic_panel-selection.v3.lock.json")

        self.manifest_validator.validate(manifest)
        calibration = panel["calibration_contract"]
        self.assertEqual(calibration["fixed_point_scale"], 10000)
        self.assertEqual(calibration["inflation_estimator"], "lo")
        self.assertEqual(
            calibration["deflation_estimator"],
            "integer-argmax-of-minimax-margin-over-floor-and-ceil-bstar",
        )
        self.assertEqual(
            calibration["deflation_bstar"],
            "U*(lo+hi)/(2*U+lo-hi)",
        )
        self.assertEqual(
            calibration["deflation_objective_output"],
            "per-candidate-bias-margin-and-exact-objective-numerator-denominator",
        )
        self.assertTrue(
            {
                "bstar.objectives",
                "bstar.comparison",
                "bstar.tie_break",
            }.issubset(calibration["required_output_fields"])
        )
        self.assertEqual(calibration["rounding_error_bound_scaled"], "1/2")
        self.assertEqual(
            calibration["rounding_robust_gate"],
            "theory4-exact-dynamic-epsilon-bound",
        )
        self.assertEqual(
            calibration["implementation"],
            "python/lupine_distill/statics/optimal_bias.py",
        )
        self.assertEqual(panel["campaign_id"], manifest["campaign_id"])

        panel_path = ROOT / manifest["execution"]["candidate_panel"]["path"]
        self.assertEqual(
            manifest["execution"]["candidate_panel"]["sha256"],
            "sha256:" + hashlib.sha256(panel_path.read_bytes()).hexdigest(),
        )
        prereg_path = ROOT / manifest["preregistration"]["input_document"]["path"]
        self.assertEqual(
            manifest["preregistration"]["input_document"]["sha256"],
            "sha256:" + hashlib.sha256(prereg_path.read_bytes()).hexdigest(),
        )

    def test_round5_v4_registers_fixed_heldout_grouping_experiment(self) -> None:
        manifest = load(
            "campaigns/v1/correction-round5-optimal-bias-grouping-heldout-v4.campaign-manifest.v1.json"
        )
        panel = load("data/candidates/round5_elastic_panel-selection.v4.lock.json")
        registry = load("registry/campaigns.v1.json")

        self.manifest_validator.validate(manifest)
        self.assertEqual(panel["campaign_id"], manifest["campaign_id"])
        self.assertFalse(panel["heldout_split_contract"]["leave_one_out"])
        self.assertEqual(
            panel["heldout_split_contract"]["ionics_rocksalt"],
            {"total": 63, "calibration": 42, "held_out_target": 21},
        )
        self.assertEqual(
            panel["heldout_split_contract"]["perovskites"],
            {"total": 62, "calibration": 41, "held_out_target": 21},
        )
        self.assertFalse(
            panel["heldout_split_contract"]["target_may_enter_any_calibration_hull"]
        )
        self.assertEqual(
            [
                key
                for key, value in panel["calibration_rules"].items()
                if isinstance(value, dict)
            ],
            [
                "class",
                "chemistry",
                "structure_prototype",
                "composition_space_neighbourhood",
                "v2_exact_tuple",
            ],
        )
        reference = panel["materials_project_reference_contract"]
        self.assertEqual(reference["disposition"], "CONDITIONALLY_ADMISSIBLE")
        self.assertEqual(reference["required_database_version"], "2026-04-13")
        self.assertIn(
            "fitting_data.num_total_strain_stress_states",
            reference["required_provenance_fields"],
        )
        self.assertTrue(any("exactly 24" in rule for rule in reference["record_acceptance"]))

        panel_path = ROOT / manifest["execution"]["candidate_panel"]["path"]
        self.assertEqual(
            manifest["execution"]["candidate_panel"]["sha256"],
            "sha256:" + hashlib.sha256(panel_path.read_bytes()).hexdigest(),
        )
        prereg_path = ROOT / manifest["preregistration"]["input_document"]["path"]
        self.assertEqual(
            manifest["preregistration"]["input_document"]["sha256"],
            "sha256:" + hashlib.sha256(prereg_path.read_bytes()).hexdigest(),
        )
        grouping = panel["grouping_derivation"]
        for path_key, hash_key in (
            ("vocabulary_path", "vocabulary_sha256"),
            ("executable_path", "executable_sha256"),
        ):
            artifact_path = ROOT / grouping[path_key]
            self.assertEqual(
                grouping[hash_key],
                "sha256:" + hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            )

        registered = [
            item
            for item in registry["campaigns"]
            if item["campaign_id"] == manifest["campaign_id"]
        ]
        self.assertEqual(registered, [manifest])
        verify_workflow = (ROOT / ".github/workflows/verify.yml").read_text(encoding="utf-8")
        self.assertIn("python/tests/test_round5_grouping.py", verify_workflow)


if __name__ == "__main__":
    unittest.main()
