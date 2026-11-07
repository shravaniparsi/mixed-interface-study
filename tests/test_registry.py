"""Synthetic harness fixtures only; these are not application research cases."""

import copy
from dataclasses import FrozenInstanceError
import json
import unittest

from mixed_interface import (
    CandidateSelector, ExecutionFeedback, ManifestError, PoolLimitExceeded,
    Strategy, generate_registry, parse_manifest,
)


def expectation(outcome="accept", category="contract"):
    return {"outcome": outcome, "category": category,
            "source": "synthetic-harness-spec:1", "statement": "Synthetic fixture requirement; not empirical evidence."}


def transformation(identifier, kind, value=None, include_value=True, expected=None):
    result = {
        "transformation_id": identifier, "kind": kind,
        "expectation": expected or expectation("reject"),
        "representations": {
            "api": {"supported": True, "action": "omit_json_property" if kind == "omit" else "set_json_value"},
            "ui": {"supported": False, "reason": "No UI mutation adapter declared for this synthetic fixture."},
        },
    }
    if include_value:
        result["value"] = value
    return result


def fixture():
    return {
        "schema_version": 1, "manifest_id": "synthetic-create-edit",
        "operations": [
            {"operation_id": "create", "interfaces": ["ui", "api"], "reference_interface": "ui",
             "input": {"article": {"title": "valid title", "body": "original body", "tags": ["fixture"]}}},
            {"operation_id": "edit", "interfaces": ["ui", "api"], "reference_interface": "ui",
             "input": {"article": {"body": "changed body"}}},
        ],
        "dependencies": [{"producer": "create", "consumer": "edit", "field_or_state": "article.id", "kind": "data",
                          "evidence": {"source": "synthetic-harness-spec:2", "statement": "Edit consumes the created ID."}}],
        "reference_expectation": expectation(),
        "constraints": [{
            "constraint_id": "create-title", "operation_id": "create", "input_path": ["article", "title"],
            "applies_to_interfaces": ["api"],
            "transformations": [
                transformation("omit", "omit", include_value=False),
                transformation("null", "null", include_value=False),
                transformation("empty", "empty", ""),
                transformation("boundary", "boundary", "x" * 17, expected=expectation("unknown", "unresolved")),
                transformation("enum", "enum", "explicit alternative", expected=expectation("accept", "implementation_control")),
            ],
        }],
        "bounds": {"max_substitutions": 2, "max_mutations": 1, "max_cases": 100},
        "cost_estimate": {"seconds": 2.0, "source": "synthetic cost fixture, not a measured run",
                          "includes": ["reset", "operations", "oracle"]},
        "oracle": {"kind": "synthetic-application-owned-oracle", "not_in_selector": True},
    }


class RegistryTests(unittest.TestCase):
    def test_complete_pool_counts_and_explicit_interface_exclusions(self):
        registry = generate_registry(fixture())
        route_only = [x for x in registry.cases if x.intervention == "route_only"]
        mutations = [x for x in registry.cases if x.intervention == "payload_mutation"]
        self.assertEqual(len(route_only), 4)
        self.assertEqual(len(mutations), 10)  # Five transformations x two API-create routes.
        self.assertEqual(len(registry.exclusions), 10)
        self.assertEqual({tuple(x.interface for x in c.operations) for c in route_only},
                         {("ui", "ui"), ("ui", "api"), ("api", "ui"), ("api", "api")})
        for case in mutations:
            self.assertEqual(case.operations[0].interface, "api")
            self.assertEqual(case.expectation_operation, "create")

    def test_route_only_inputs_do_not_change(self):
        original = fixture()
        registry = generate_registry(original)
        for case in registry.cases:
            if case.intervention == "route_only":
                self.assertIn("::route-only::", case.case_id)
                self.assertIsNone(case.mutation_json)
                for operation, declared in zip(case.operations, original["operations"]):
                    self.assertEqual(operation.to_dict()["input"], declared["input"])

    def test_omission_null_and_empty_remain_distinct(self):
        registry = generate_registry(fixture())
        cases = {}
        for case in registry.cases:
            if case.intervention == "payload_mutation" and case.operations[1].interface == "ui":
                mutation = json.loads(case.mutation_json)
                cases[mutation["kind"]] = case.operations[0].to_dict()["input"]["article"]
                self.assertIn("::payload-mutation::", case.case_id)
        self.assertNotIn("title", cases["omit"])
        self.assertIsNone(cases["null"]["title"])
        self.assertEqual(cases["empty"]["title"], "")
        self.assertEqual(cases["boundary"]["title"], "x" * 17)
        self.assertEqual(cases["enum"]["title"], "explicit alternative")

    def test_deterministic_under_object_and_catalog_order_changes(self):
        first = fixture()
        second = copy.deepcopy(first)
        second["operations"][0]["interfaces"].reverse()
        second["constraints"][0]["transformations"].reverse()
        second["cost_estimate"]["includes"].reverse()
        second = dict(reversed(list(second.items())))
        self.assertEqual(generate_registry(first).to_json(), generate_registry(second).to_json())

    def test_registry_detaches_mutable_inputs_and_returns_copies(self):
        raw = fixture()
        registry = generate_registry(raw)
        original = registry.to_json()
        raw["operations"][0]["input"]["article"]["tags"].append("new")
        copy_out = registry.to_dict()
        copy_out["cases"][0]["operations"][0]["input"]["article"]["tags"].append("other")
        self.assertEqual(registry.to_json(), original)
        with self.assertRaises(FrozenInstanceError):
            registry.cases[0].case_id = "changed"

    def test_expectation_scope_and_authority_are_preserved_not_inferred(self):
        registry = generate_registry(fixture())
        by_kind = {json.loads(x.mutation_json)["kind"]: x for x in registry.cases if x.mutation_json}
        self.assertEqual(by_kind["enum"].expectation.category, "implementation_control")
        self.assertEqual(by_kind["enum"].expectation.outcome, "accept")
        self.assertEqual(by_kind["boundary"].expectation.outcome, "unknown")
        self.assertEqual(by_kind["boundary"].expectation.category, "unresolved")
        self.assertEqual(by_kind["omit"].to_dict()["expectation_scope"], {"kind": "operation", "operation_id": "create"})
        self.assertEqual(registry.cases[0].to_dict()["expectation_scope"], {"kind": "workflow"})

    def test_selector_pool_has_no_expectation_or_defect_labels(self):
        registry = generate_registry(fixture())
        for candidate in registry.selection_pool:
            self.assertFalse(hasattr(candidate, "expectation"))
            self.assertFalse(hasattr(candidate, "defect_label"))
        pools = [CandidateSelector(registry.selection_pool, strategy, seed=3) for strategy in Strategy]
        self.assertTrue(all(x.candidate_ids == pools[0].candidate_ids for x in pools))
        selector = pools[-1]
        chosen = selector.select_next()
        self.assertFalse(selector.covered_obligations)
        selector.record_feedback(ExecutionFeedback(chosen.case_id, {"create"}))
        self.assertFalse(selector.covered_dependencies)

    def test_generated_targets_match_route_and_allow_observed_feedback(self):
        registry = generate_registry(fixture())
        case = next(x for x in registry.cases if tuple(y.interface for y in x.operations) == ("api", "ui"))
        obligation = next(iter(case.candidate.obligations))
        self.assertEqual((obligation.producer_interface, obligation.consumer_interface), ("api", "ui"))
        selector = CandidateSelector([case.candidate], Strategy.DEPENDENCY_GREEDY)
        selector.select_next()
        selector.record_feedback(ExecutionFeedback(case.case_id, {"create", "edit"}, exercised_obligations={obligation}))
        self.assertEqual(selector.covered_dependencies, case.candidate.dependencies)

    def test_substitution_and_mutation_bounds(self):
        raw = fixture()
        raw["bounds"]["max_substitutions"] = 1
        raw["bounds"]["max_mutations"] = 0
        registry = generate_registry(raw)
        self.assertEqual(len(registry.cases), 3)
        self.assertTrue(all(x.substitutions <= 1 and x.mutation_json is None for x in registry.cases))
        raw["bounds"]["max_substitutions"] = 0
        self.assertEqual(len(generate_registry(raw).cases), 1)

    def test_cap_fails_instead_of_returning_a_biased_truncation(self):
        raw = fixture()
        raw["bounds"]["max_cases"] = 13
        with self.assertRaises(PoolLimitExceeded):
            generate_registry(raw)
        raw["bounds"]["max_cases"] = 14
        self.assertEqual(len(generate_registry(raw).cases), 14)

    def test_no_implicit_boundary_values_or_transformations(self):
        raw = fixture()
        del raw["constraints"][0]["transformations"][3]["value"]
        with self.assertRaisesRegex(ManifestError, "explicitly declared value"):
            generate_registry(raw)
        raw = fixture()
        raw["constraints"][0]["transformations"][0]["kind"] = "random_fuzz"
        with self.assertRaisesRegex(ManifestError, "unsupported transformation"):
            generate_registry(raw)

    def test_explicit_representation_required_and_ui_mutations_not_guessed(self):
        raw = fixture()
        del raw["constraints"][0]["transformations"][0]["representations"]["ui"]
        with self.assertRaises(ManifestError):
            generate_registry(raw)
        raw = fixture()
        raw["constraints"][0]["applies_to_interfaces"] = ["ui", "api"]
        with self.assertRaisesRegex(ManifestError, "API payload mutations only"):
            generate_registry(raw)

    def test_provenance_required_and_unknown_not_promoted_to_rejection(self):
        raw = fixture()
        del raw["constraints"][0]["transformations"][0]["expectation"]["category"]
        with self.assertRaises(ManifestError):
            generate_registry(raw)
        raw = fixture()
        raw["reference_expectation"]["source"] = ""
        with self.assertRaises(ManifestError):
            generate_registry(raw)
        raw = fixture()
        raw["reference_expectation"] = expectation("reject", "unresolved")
        with self.assertRaisesRegex(ManifestError, "unresolved expectations unknown"):
            generate_registry(raw)

    def test_unknown_fields_and_result_labels_are_rejected(self):
        raw = fixture()
        raw["known_defect_label"] = True
        with self.assertRaisesRegex(ManifestError, "unsupported"):
            generate_registry(raw)

    def test_noop_and_duplicate_mutations_are_rejected(self):
        raw = fixture()
        raw["constraints"][0]["transformations"][3]["value"] = "valid title"
        with self.assertRaisesRegex(ManifestError, "does not change input"):
            generate_registry(raw)
        raw = fixture()
        raw["constraints"][0]["transformations"][3]["value"] = ""
        with self.assertRaisesRegex(ManifestError, "duplicate mutation effect"):
            generate_registry(raw)

    def test_mutation_path_must_exist_and_preserves_other_inputs(self):
        raw = fixture()
        raw["constraints"][0]["input_path"] = ["article", "missing"]
        with self.assertRaisesRegex(ManifestError, "existing object property"):
            generate_registry(raw)
        registry = generate_registry(fixture())
        for case in registry.cases:
            self.assertEqual(case.operations[0].to_dict()["input"]["article"]["body"], "original body")
            self.assertEqual(case.operations[1].to_dict()["input"], {"article": {"body": "changed body"}})

    def test_dependencies_require_declared_ordered_endpoints(self):
        raw = fixture()
        raw["dependencies"][0]["consumer"] = "missing"
        with self.assertRaisesRegex(ManifestError, "declared operations"):
            generate_registry(raw)
        raw = fixture()
        raw["dependencies"][0]["producer"] = "edit"
        raw["dependencies"][0]["consumer"] = "create"
        with self.assertRaisesRegex(ManifestError, "must precede"):
            generate_registry(raw)

    def test_unsupported_multi_mutation_and_bad_cost_rejected(self):
        for change in ("multi", "zero", "nan", "cost_scope"):
            raw = fixture()
            if change == "multi": raw["bounds"]["max_mutations"] = 2
            if change == "zero": raw["cost_estimate"]["seconds"] = 0
            if change == "nan": raw["cost_estimate"]["seconds"] = float("nan")
            if change == "cost_scope": raw["cost_estimate"]["includes"] = ["operations"]
            with self.subTest(change=change), self.assertRaises(ManifestError):
                generate_registry(raw)

    def test_manifest_round_trip_is_canonical(self):
        parsed = parse_manifest(fixture())
        self.assertEqual(generate_registry(parsed.to_dict()).to_json(), generate_registry(fixture()).to_json())
        self.assertEqual(json.loads(generate_registry(fixture()).to_json())["status"], "generated_not_executed")


if __name__ == "__main__":
    unittest.main()
