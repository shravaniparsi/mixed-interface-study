"""Offline consistency checks against registered inputs, never execution results."""

import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path

from mixed_interface import generate_registry


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MUTATIONS = {
    "article-body-omitted", "article-body-null", "article-body-empty",
    "article-body-whitespace", "article-tags-omitted", "article-title-150",
    "article-title-151",
}


class RealWorldRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_bytes = (ROOT / "manifests/realworld-boundary-registry-v1.json").read_bytes()
        cls.source = json.loads(cls.source_bytes)
        cls.registered = {case["candidate_id"]: case for case in cls.source["cases"]}
        cls.manifest = json.loads((ROOT / "manifests/realworld-article-generation-v1.json").read_text())
        cls.registry = generate_registry(cls.manifest)

    def test_complete_bounded_pool_and_reproducible_artifact(self):
        self.assertEqual(Counter(case.intervention for case in self.registry.cases),
                         {"route_only": 4, "payload_mutation": 14})
        self.assertEqual(len(self.registry.exclusions), 14)
        saved = ROOT / "manifests/realworld-article-generated-pool-v1.json"
        self.assertEqual(saved.read_text(), self.registry.to_json())

    def test_every_generated_producer_matches_its_registered_input_and_expectation(self):
        seen = Counter()
        routes = set()
        for case in self.registry.cases:
            producer, consumer = [operation.to_dict() for operation in case.operations]
            if case.mutation_json is None:
                self.assertEqual(producer["input"]["article"], self.registered["article-valid"]["prefix_payload"])
                routes.add((producer["interface"], consumer["interface"]))
                continue
            source_id = json.loads(case.mutation_json)["transformation_id"]
            self.assertIn(source_id, EXPECTED_MUTATIONS)
            self.assertEqual(producer["interface"], "api")
            self.assertEqual(producer["input"]["article"], self.registered[source_id]["prefix_payload"])
            self.assertEqual(case.expectation.to_dict(), self.registered[source_id]["expectation"])
            self.assertEqual(case.expectation_operation, "create_article")
            seen[(source_id, consumer["interface"])] += 1
        self.assertEqual(routes, {("ui", "ui"), ("ui", "api"), ("api", "ui"), ("api", "api")})
        self.assertEqual(seen, Counter({(source_id, interface): 1
                                      for source_id in EXPECTED_MUTATIONS for interface in ("ui", "api")}))

    def test_consumer_bundle_bindings_preserve_producer_fields(self):
        consumer = self.manifest["operations"][1]
        self.assertEqual(set(consumer["input"]["article"]), {"title", "description", "body", "tagList"})
        self.assertNotEqual(consumer["input"]["article"]["body"],
                            self.registered["article-valid"]["prefix_payload"]["body"])
        bindings = self.manifest["oracle"]["output_bindings"]
        self.assertTrue(all(item["required_before_execution"] for item in bindings))
        self.assertEqual({tuple(item["source_path"]) for item in bindings},
                         {("article", field) for field in ("slug", "title", "description", "tagList")})
        self.assertTrue(all(item["target_operation"] == consumer["operation_id"] for item in bindings))

    def test_provenance_unknown_boundaries_and_placeholder_cost_are_retained(self):
        oracle = self.manifest["oracle"]
        self.assertEqual(oracle["source_registry"]["sha256"], hashlib.sha256(self.source_bytes).hexdigest())
        self.assertEqual(oracle["cost_status"], "unmeasured_uniform_placeholder")
        self.assertIn("UNMEASURED PLACEHOLDER", self.manifest["cost_estimate"]["source"])
        self.assertEqual(self.registry.to_dict()["status"], "generated_not_executed")
        for case in self.registry.cases:
            if case.mutation_json and json.loads(case.mutation_json)["transformation_id"] in {"article-title-150", "article-title-151"}:
                self.assertEqual((case.expectation.outcome, case.expectation.category), ("unknown", "unresolved"))

    def test_ui_mutations_are_explicitly_excluded_without_claiming_unrepresentability(self):
        for constraint in self.manifest["constraints"]:
            self.assertEqual(constraint["applies_to_interfaces"], ["api"])
            for transform in constraint["transformations"]:
                ui = transform["representations"]["ui"]
                self.assertFalse(ui["supported"])
                self.assertIn("reason", ui)
                if transform["kind"] not in ("omit", "null"):
                    self.assertIn("adapter restriction", ui["reason"])
                    self.assertIn("does not claim inherent UI impossibility", ui["reason"])


if __name__ == "__main__":
    unittest.main()
