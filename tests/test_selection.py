import unittest

from mixed_interface import (
    Candidate, CandidateSelector, DependencyEdge, ExecutionFeedback,
    RouteObligation, Strategy,
)


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.article = DependencyEdge("create_article", "edit_article", "title")
        self.comment = DependencyEdge("create_comment", "delete_comment", "comment_id")
        self.ui_ui = RouteObligation(self.article, "ui", "ui")
        self.api_ui = RouteObligation(self.article, "api", "ui")
        self.comment_ui_api = RouteObligation(self.comment, "ui", "api")
        self.anchor = Candidate("anchor", {self.article}, {self.ui_ui}, 0.1)
        self.alternate = Candidate("alternate", {self.article}, {self.api_ui}, 1)
        self.new_edge = Candidate("new_edge", {self.comment}, {self.comment_ui_api}, 2)
        self.pool = [self.anchor, self.alternate, self.new_edge]

    def completed(self, candidate):
        return ExecutionFeedback(
            candidate.case_id,
            {op for edge in candidate.dependencies for op in (edge.producer, edge.consumer)},
            candidate.dependencies, candidate.obligations,
        )

    def exhaust(self, selector):
        result = []
        while True:
            candidate = selector.select_next()
            if candidate is None:
                return result
            result.append(candidate.case_id)
            selector.record_feedback(self.completed(candidate))

    def test_all_strategies_receive_and_exhaust_identical_pool(self):
        for strategy in Strategy:
            with self.subTest(strategy=strategy):
                selector = CandidateSelector(self.pool, strategy, seed=12)
                self.assertEqual(selector.candidate_ids, ("alternate", "anchor", "new_edge"))
                result = self.exhaust(selector)
                self.assertEqual(set(result), set(selector.candidate_ids))
                self.assertEqual(len(result), 3)
                self.assertTrue(selector.exhausted)
                self.assertIsNone(selector.select_next())

    def test_seeded_order_is_reproducible_and_input_order_independent(self):
        pool = [Candidate("case_{}".format(i), {self.article}, {self.api_ui}, 1) for i in range(12)]
        for strategy in Strategy:
            with self.subTest(strategy=strategy):
                a = CandidateSelector(pool, strategy, seed=31)
                b = CandidateSelector(reversed(pool), strategy, seed=31)
                self.assertEqual(self.exhaust(a), self.exhaust(b))

    def test_route_guidance_differs_from_generic_dependencies_after_feedback(self):
        generic = CandidateSelector(self.pool, Strategy.DEPENDENCY_GREEDY, seed=7)
        route = CandidateSelector(self.pool, Strategy.ROUTE_GREEDY, seed=7)
        for selector in (generic, route):
            selected = selector.select_next()
            self.assertEqual(selected.case_id, "anchor")
            selector.record_feedback(self.completed(selected))
        # Generic selects a new edge; route selection chooses the cheaper,
        # untested API-to-UI route through the already exercised edge.
        self.assertEqual(generic.select_next().case_id, "new_edge")
        self.assertEqual(route.select_next().case_id, "alternate")

    def test_selecting_does_not_mark_predictions_as_coverage(self):
        selector = CandidateSelector(self.pool, Strategy.ROUTE_GREEDY)
        selector.select_next()
        self.assertFalse(selector.covered_dependencies)
        self.assertFalse(selector.covered_obligations)

    def test_reaching_operations_without_consumption_evidence_does_not_cover_edge(self):
        selector = CandidateSelector([self.anchor], Strategy.ROUTE_GREEDY)
        selector.select_next()
        selector.record_feedback(ExecutionFeedback("anchor", {"create_article", "edit_article"}))
        self.assertFalse(selector.covered_dependencies)
        self.assertFalse(selector.covered_obligations)

    def test_early_failure_can_record_empty_coverage(self):
        selector = CandidateSelector([self.anchor], Strategy.DEPENDENCY_GREEDY)
        selector.select_next()
        selector.record_feedback(ExecutionFeedback("anchor", {"create_article"}))
        self.assertFalse(selector.covered_dependencies)

    def test_cannot_report_coverage_before_consumer_reached(self):
        with self.assertRaisesRegex(ValueError, "both endpoints"):
            ExecutionFeedback("anchor", {"create_article"}, exercised_obligations={self.ui_ui})

    def test_observed_route_implies_generic_edge_but_not_other_route(self):
        selector = CandidateSelector([self.anchor], Strategy.ROUTE_GREEDY)
        selector.select_next()
        selector.record_feedback(ExecutionFeedback(
            "anchor", {"create_article", "edit_article"}, exercised_obligations={self.ui_ui}
        ))
        self.assertEqual(selector.covered_dependencies, frozenset({self.article}))
        self.assertEqual(selector.covered_obligations, frozenset({self.ui_ui}))
        self.assertNotIn(self.api_ui, selector.covered_obligations)

    def test_feedback_rejects_unselected_duplicate_and_undeclared_targets(self):
        selector = CandidateSelector([self.anchor], Strategy.ROUTE_GREEDY)
        with self.assertRaisesRegex(ValueError, "previously selected"):
            selector.record_feedback(self.completed(self.anchor))
        selector.select_next()
        with self.assertRaisesRegex(ValueError, "undeclared route"):
            selector.record_feedback(ExecutionFeedback(
                "anchor", {"create_article", "edit_article"}, exercised_obligations={self.api_ui}
            ))
        self.assertFalse(selector.covered_dependencies)
        selector.record_feedback(self.completed(self.anchor))
        with self.assertRaisesRegex(ValueError, "already been recorded"):
            selector.record_feedback(self.completed(self.anchor))

    def test_positive_finite_cost_required(self):
        for cost in (0, -1, float("nan"), float("inf"), True, "invalid"):
            with self.subTest(cost=cost), self.assertRaises(ValueError):
                Candidate("bad", {self.article}, {self.ui_ui}, cost)

    def test_obligations_require_declared_edges_and_valid_interfaces(self):
        with self.assertRaisesRegex(ValueError, "declared dependency"):
            Candidate("bad", set(), {self.ui_ui}, 1)
        with self.assertRaises(ValueError):
            RouteObligation(self.article, "ui", "database")

    def test_duplicate_ids_rejected_and_empty_pool_supported(self):
        with self.assertRaisesRegex(ValueError, "duplicate case_id"):
            CandidateSelector([self.anchor, self.anchor], Strategy.RANDOM)
        empty = CandidateSelector([], Strategy.ROUTE_GREEDY)
        self.assertTrue(empty.exhausted)
        self.assertIsNone(empty.select_next())

    def test_zero_marginal_candidates_are_not_silently_dropped(self):
        pool = [Candidate("a", {self.article}, {self.ui_ui}, 1),
                Candidate("b", {self.article}, {self.ui_ui}, 1)]
        selector = CandidateSelector(pool, Strategy.ROUTE_GREEDY)
        first = selector.select_next()
        selector.record_feedback(self.completed(first))
        self.assertIsNotNone(selector.select_next())
        self.assertEqual(selector.decisions[-1].marginal_targets, 0)
        self.assertTrue(selector.exhausted)

    def test_ratios_use_execution_cost_not_raw_target_count(self):
        expensive = Candidate("expensive", {self.article, self.comment},
                              {self.ui_ui, self.comment_ui_api}, 10)
        cheap = Candidate("cheap", {self.article}, {self.api_ui}, 1)
        for strategy in (Strategy.DEPENDENCY_GREEDY, Strategy.ROUTE_GREEDY):
            selector = CandidateSelector([expensive, cheap], strategy)
            self.assertEqual(selector.select_next().case_id, "cheap")
            self.assertEqual(selector.decisions[-1].targets_per_second, 1)

    def test_candidate_collections_are_frozen_from_caller_mutation(self):
        edges = {self.article}
        obligations = {self.ui_ui}
        candidate = Candidate("case", edges, obligations, 1)
        edges.clear()
        obligations.clear()
        self.assertEqual(candidate.dependencies, frozenset({self.article}))
        self.assertEqual(candidate.obligations, frozenset({self.ui_ui}))


if __name__ == "__main__":
    unittest.main()
