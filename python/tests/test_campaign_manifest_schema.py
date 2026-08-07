"""Acceptance tests for the campaign-manifest v1 JSON Schema."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from fractions import Fraction
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[2]
GROUPING_SPEC = importlib.util.spec_from_file_location(
    "round5_grouping", ROOT / "tools/round5_grouping.py"
)
assert GROUPING_SPEC is not None and GROUPING_SPEC.loader is not None
GROUPING_MODULE = importlib.util.module_from_spec(GROUPING_SPEC)
GROUPING_SPEC.loader.exec_module(GROUPING_MODULE)
GroupingRefusalError = GROUPING_MODULE.GroupingRefusalError
derive_groupings = GROUPING_MODULE.derive_groupings
load_vocabulary = GROUPING_MODULE.load_vocabulary


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
                "correction-round5-sharp-v2",
                "correction-round5-sharp-v3",
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

    def test_round5_v3_groupings_are_order_reduction_and_boundary_stable(self) -> None:
        vocabulary = load_vocabulary()
        candidate = {
            "class": "ionics-rocksalt",
            "structure_prototype": "AB_cF8_225_a_b",
            "elemental_composition": {"Cl": 2, "Na": 2},
        }
        reordered = {
            "class": "ionics-rocksalt",
            "structure_prototype": "AB_cF8_225_a_b",
            "elemental_composition": {"Na": 1, "Cl": 1},
        }
        expected = {
            "class": "ionics-rocksalt",
            "chemistry": "Na-Cl",
            "structure_prototype": "AB_cF8_225_a_b",
            "composition_space_neighbourhood": "csn-zband10-v1:Z011-020=1",
        }
        self.assertEqual(derive_groupings(candidate, vocabulary), expected)
        self.assertEqual(derive_groupings(reordered, vocabulary), expected)

        boundary = derive_groupings(
            {
                "class": "ionics-rocksalt",
                "structure_prototype": "AB_cF8_225_a_b",
                "elemental_composition": {"Ne": 1, "Na": 1},
            },
            vocabulary,
        )
        self.assertEqual(boundary["chemistry"], "Ne-Na")
        self.assertEqual(
            boundary["composition_space_neighbourhood"],
            "csn-zband10-v1:Z001-010=1,Z011-020=1",
        )

    def test_round5_v3_grouping_adversarial_inputs_refuse(self) -> None:
        base = {
            "class": "ionics-rocksalt",
            "structure_prototype": "AB_cF8_225_a_b",
            "elemental_composition": {"Na": 1, "Cl": 1},
        }
        cases = [
            ({**base, "class": "Ionics-Rocksalt"}, "REFUSE_CLASS_VOCABULARY"),
            ({**base, "structure_prototype": "rocksalt"}, "REFUSE_CLASS_PROTOTYPE_MISMATCH"),
            ({**base, "elemental_composition": {}}, "REFUSE_EMPTY_COMPOSITION"),
            ({**base, "elemental_composition": {"Xx": 1}}, "REFUSE_UNKNOWN_ELEMENT"),
            ({**base, "elemental_composition": {"Na": True}}, "REFUSE_NON_INTEGER_STOICHIOMETRY"),
            ({**base, "elemental_composition": {"Na": 0}}, "REFUSE_NON_POSITIVE_STOICHIOMETRY"),
            ({**base, "elemental_composition": {"Na": 0.5}}, "REFUSE_NON_INTEGER_STOICHIOMETRY"),
        ]
        for candidate, code in cases:
            with self.subTest(code=code), self.assertRaises(GroupingRefusalError) as raised:
                derive_groupings(candidate)
            self.assertEqual(raised.exception.code, code)

    def test_round5_v3_contract_separates_rules_and_binds_provenance(self) -> None:
        manifest = load("campaigns/v1/correction-round5-sharp-v3.campaign-manifest.v1.json")
        panel = load("data/candidates/round5_elastic_panel-selection.v3.lock.json")
        self.manifest_validator.validate(manifest)
        registry = load("registry/campaigns.v1.json")
        registered = [
            item for item in registry["campaigns"] if item["campaign_id"] == manifest["campaign_id"]
        ]
        self.assertEqual(registered, [manifest])

        panel_path = ROOT / manifest["execution"]["candidate_panel"]["path"]
        prereg_path = ROOT / manifest["preregistration"]["input_document"]["path"]
        self.assertEqual(
            manifest["execution"]["candidate_panel"]["sha256"],
            "sha256:" + hashlib.sha256(panel_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            manifest["preregistration"]["input_document"]["sha256"],
            "sha256:" + hashlib.sha256(prereg_path.read_bytes()).hexdigest(),
        )

        grouping = panel["grouping_derivation"]
        for key in ("vocabulary", "executable"):
            path = ROOT / grouping[f"{key}_path"]
            self.assertEqual(
                grouping[f"{key}_sha256"],
                "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        self.assertEqual(
            grouping["required_rules"],
            ["class", "chemistry", "structure_prototype", "composition_space_neighbourhood"],
        )

        rules = panel["calibration_rules"]
        self.assertEqual(rules["class"]["role"], "V3_PRIMARY_CONFIRMATORY")
        self.assertEqual(rules["chemistry"]["role"], "REGISTERED_SECONDARY")
        self.assertEqual(rules["structure_prototype"]["role"], "REGISTERED_SECONDARY")
        self.assertEqual(rules["composition_space_neighbourhood"]["role"], "REGISTERED_SECONDARY")
        self.assertEqual(rules["v2_exact_tuple"]["role"], "IMMUTABLE_V2_DIAGNOSTIC_NOT_V3_CONFIRMATORY")
        self.assertEqual(rules["minimum_other_structures"], 4)

        reference = panel["materials_project_reference_contract"]
        self.assertEqual(reference["disposition"], "CONDITIONALLY_ADMISSIBLE")
        self.assertEqual(reference["required_database_version"], "2026-04-13")
        self.assertEqual(reference["discovery_counts"], "NOT_REGISTERED_INPUT_AND_NOT_ACCEPTANCE_EVIDENCE")
        required = set(reference["required_provenance_fields"])
        self.assertTrue(
            {
                "raw_query_sha256",
                "builder_meta.database_version",
                "material_id",
                "origins",
                "structure",
                "elastic_tensor.ieee_format",
                "fitting_data.optimization_task",
                "fitting_data.deformation_tasks",
            }.issubset(required)
        )
        self.assertEqual(
            panel["theory_binding"]["open_pull_request"],
            "EXECUTION_REFUSE_THEOREM_NOT_LANDED",
        )
        self.assertEqual(panel["analysis_requirements"]["primary_grouping_rule"], "class")
        self.assertEqual(panel["analysis_requirements"]["minimum_secondary_non_tied_structures"], 16)

    def test_round5_v3_sharp_boundaries_remain_strict(self) -> None:
        unit = 10_000

        def licensed(lo: int, hi: int, median: int) -> bool:
            if unit < lo:
                return median * (2 * unit - lo) < lo * unit
            if hi < unit:
                return hi * (unit + median) < 2 * unit * median
            return False

        self.assertFalse(licensed(12_000, 13_000, 15_000))
        self.assertTrue(licensed(12_000, 13_000, 14_999))
        self.assertFalse(licensed(4_000, 7_500, 6_000))
        self.assertTrue(licensed(4_000, 7_500, 6_001))
        self.assertFalse(licensed(unit, unit, unit))


if __name__ == "__main__":
    unittest.main()
