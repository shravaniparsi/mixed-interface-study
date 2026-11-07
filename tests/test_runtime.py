"""Controller-only tests with a deterministic clock; no application execution."""

import json
import unittest
from dataclasses import FrozenInstanceError, replace
from unittest.mock import patch

from mixed_interface import CandidateSelector, DependencyEdge, ExecutionFeedback, Strategy, generate_registry
from mixed_interface.runtime import CaseExecution, ExecutionCancelled, run_registry
from test_registry import fixture


class Clock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


def observed(case):
    return ExecutionFeedback(case.case_id, frozenset(operation.operation_id for operation in case.operations),
                             exercised_obligations=case.candidate.obligations)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.registry = generate_registry(fixture())
        self.clock = Clock()

    def run_cases(self, callback, budget=10.0, **kwargs):
        return run_registry(self.registry, kwargs.pop("strategy", Strategy.RANDOM), kwargs.pop("seed", 11),
                            budget, callback, resource_id="synthetic-fixture-v1", clock=self.clock,
                            **kwargs).to_dict()

    def test_same_pool_oracle_resources_and_exclusions_across_strategies(self):
        reports = [self.run_cases(lambda case, remaining: CaseExecution("completed", {"defect": True}),
                                  strategy=strategy, seed=29, resource_metadata={"fixture_sha": "synthetic"},
                                  setup_metadata={"fixed_host_setup_s": 100}) for strategy in Strategy]
        self.assertEqual(len({report["hashes"]["comparison_context_sha256"] for report in reports}), 1)
        expected = {case.case_id for case in self.registry.cases}
        for report in reports:
            self.assertEqual(set(report["execution_order"]), expected)
            self.assertEqual(report["stop_reason"], "pool_exhausted")
            self.assertEqual(report["excluded_combinations"], [x.to_dict() for x in self.registry.exclusions])
            self.assertEqual(report["observed_coverage"], {"dependencies": [], "obligations": []})
            self.assertEqual(report["fixed_common_setup"]["budget_scope"], "outside")

    def test_outcomes_are_not_selector_input_and_seeded_order_is_reproducible(self):
        for strategy in Strategy:
            first = self.run_cases(lambda case, remaining: CaseExecution("completed", {"defect": True}), strategy=strategy)
            second = self.run_cases(lambda case, remaining: CaseExecution("completed", {"defect": False}), strategy=strategy)
            self.assertEqual(first["execution_order"], second["execution_order"])
        other = self.run_cases(lambda case, remaining: CaseExecution("completed", None), seed=47)
        same = self.run_cases(lambda case, remaining: CaseExecution("completed", None), seed=11)
        self.assertNotEqual(other["execution_order"], same["execution_order"])

    def test_actual_time_not_estimates_controls_budget_and_exact_deadline_is_timely(self):
        self.registry = replace(self.registry, cases=tuple(replace(case, candidate=replace(case.candidate, estimated_cost_s=1000))
                                                          for case in self.registry.cases))
        allowances = []
        def execute(case, remaining):
            allowances.append(remaining)
            self.clock.advance(0.25)
            return CaseExecution("completed", "observed", observed(case))
        report = self.run_cases(execute, budget=0.5)
        self.assertEqual(allowances, [0.5, 0.25])
        self.assertEqual(report["elapsed_s"], 0.5)
        self.assertEqual(report["stop_reason"], "budget_exhausted")
        self.assertTrue(all(case["feedback_credited"] for case in report["cases"]))
        self.assertEqual([case["actual_cost_s"] for case in report["cases"]], [0.25, 0.25])

    def test_reset_startup_oracle_teardown_overrun_is_measured_and_never_credited(self):
        def execute(case, remaining):
            for phase in (0.125, 0.125, 0.25, 0.25, 0.5):
                self.clock.advance(phase)
            return CaseExecution("completed", "oracle_passed", observed(case))
        report = self.run_cases(execute, budget=1)
        self.assertEqual(report["elapsed_s"], 1.25)
        self.assertEqual(report["deadline_overrun_s"], 0.25)
        self.assertEqual(len(report["execution_order"]), 1)
        case = report["cases"][0]
        self.assertEqual((case["status"], case["callback_status"]), ("timeout", "completed"))
        self.assertEqual(case["failure_classification"], "deadline_overrun")
        self.assertFalse(case["feedback_credited"])
        self.assertEqual(report["observed_coverage"], {"dependencies": [], "obligations": []})

    def test_deadline_crossed_during_selection_does_not_invoke_callback(self):
        clock = self.clock
        class SlowSelector(CandidateSelector):
            def select_next(self):
                clock.advance(1)
                return super().select_next()
        with patch("mixed_interface.runtime.CandidateSelector", SlowSelector):
            report = self.run_cases(lambda *args: self.fail("must not invoke callback"), budget=1)
        self.assertEqual(report["execution_order"], [])
        self.assertEqual(len(report["selection_order"]), 1)
        self.assertEqual(report["cases"][0]["failure_classification"], "deadline_before_start")

    def test_cancellation_before_selection_and_between_selection_and_start(self):
        report = self.run_cases(lambda *args: self.fail("cancelled"), cancel_requested=lambda: True)
        self.assertEqual((report["stop_reason"], report["selection_order"]), ("cancelled", []))
        polls = iter((False, True))
        report = self.run_cases(lambda *args: self.fail("cancelled"), cancel_requested=lambda: next(polls))
        self.assertEqual(report["execution_order"], [])
        self.assertEqual(report["cases"][0]["failure_classification"], "cancelled_before_start")

    def test_adapter_termination_statuses_stop_run_and_do_not_credit_feedback(self):
        for status in ("timeout", "cancelled", "error"):
            report = self.run_cases(lambda case, remaining: CaseExecution(status, "adapter_result", observed(case)))
            self.assertEqual(len(report["cases"]), 1)
            self.assertEqual(report["cases"][0]["failure_classification"], "adapter_" + status)
            self.assertFalse(report["cases"][0]["feedback_credited"])
            self.assertEqual(report["observed_coverage"], {"dependencies": [], "obligations": []})

    def test_timeout_cancellation_and_callback_exception_are_classified(self):
        for error, classification in ((TimeoutError(), "callback_timeout"),
                                      (ExecutionCancelled(), "callback_cancelled"),
                                      (RuntimeError("synthetic"), "callback_exception")):
            def execute(case, remaining):
                self.clock.advance(0.25)
                raise error
            report = self.run_cases(execute)
            self.assertEqual(report["cases"][0]["actual_cost_s"], 0.25)
            self.assertEqual(report["cases"][0]["failure_classification"], classification)

    def test_invalid_callback_result_stops_with_error(self):
        report = self.run_cases(lambda case, remaining: {"passed": True})
        self.assertEqual(report["stop_reason"], "execution_error")
        self.assertEqual(report["cases"][0]["failure_classification"], "invalid_callback_result")

    def test_feedback_for_a_different_previously_selected_case_is_rejected(self):
        previous = []
        def execute(case, remaining):
            if previous:
                return CaseExecution("completed", None, observed(previous[0]))
            previous.append(case)
            return CaseExecution("completed", None)
        report = self.run_cases(execute)
        self.assertEqual(len(report["cases"]), 2)
        self.assertEqual(report["cases"][-1]["failure_classification"], "invalid_feedback")
        self.assertEqual(report["observed_coverage"], {"dependencies": [], "obligations": []})

    def test_undeclared_operations_and_edges_cannot_create_coverage(self):
        def operation(case):
            return ExecutionFeedback(case.case_id, frozenset({"imaginary"}))
        def edge(case):
            return ExecutionFeedback(case.case_id, frozenset({"create", "edit"}),
                                     frozenset({DependencyEdge("create", "edit", "undeclared")}))
        for feedback in (operation, edge):
            report = self.run_cases(lambda case, remaining: CaseExecution("completed", None, feedback(case)))
            self.assertEqual(report["cases"][0]["failure_classification"], "invalid_feedback")
            self.assertEqual(report["observed_coverage"], {"dependencies": [], "obligations": []})

    def test_reaching_operations_alone_does_not_establish_consumption(self):
        report = self.run_cases(lambda case, remaining: CaseExecution("completed", "reached",
                                ExecutionFeedback(case.case_id, frozenset({"create", "edit"}))))
        self.assertEqual(report["observed_coverage"], {"dependencies": [], "obligations": []})

    def test_timely_observed_route_feedback_counts_only_its_declared_targets(self):
        report = self.run_cases(lambda case, remaining: CaseExecution("completed", "observation", observed(case)))
        self.assertEqual(len(report["observed_coverage"]["dependencies"]), 1)
        self.assertEqual(len(report["observed_coverage"]["obligations"]), 4)
        self.assertTrue(all(case["feedback_credited"] for case in report["cases"]))

    def test_effective_calibrated_costs_change_pool_hash_without_mutating_manifest(self):
        first = self.run_cases(lambda case, remaining: CaseExecution("completed", None))
        self.registry = replace(self.registry, cases=tuple(replace(case, candidate=replace(case.candidate, estimated_cost_s=0.125))
                                                          for case in self.registry.cases))
        second = self.run_cases(lambda case, remaining: CaseExecution("completed", None))
        self.assertEqual(first["hashes"]["manifest_sha256"], second["hashes"]["manifest_sha256"])
        self.assertNotEqual(first["hashes"]["effective_pool_sha256"], second["hashes"]["effective_pool_sha256"])
        self.assertTrue(all(case["estimated_cost_s"] == 0.125 for case in second["cases"]))

    def test_context_changes_for_resources_or_setup_but_not_seed(self):
        execute = lambda case, remaining: CaseExecution("completed", None)
        base = self.run_cases(execute)
        seed = self.run_cases(execute, seed=47)
        changed = self.run_cases(execute, resource_metadata={"fixture": "different"})
        setup = self.run_cases(execute, setup_metadata={"environment": "different"})
        key = "comparison_context_sha256"
        self.assertEqual(base["hashes"][key], seed["hashes"][key])
        self.assertNotEqual(base["hashes"][key], changed["hashes"][key])
        self.assertNotEqual(base["hashes"][key], setup["hashes"][key])

    def test_result_and_report_json_are_detached_and_frozen(self):
        outcome, details = {"observed": ["synthetic"]}, {"trace": [1]}
        result = CaseExecution("completed", outcome, details=details)
        outcome["observed"].clear()
        details["trace"].append(2)
        self.assertEqual(result.outcome, {"observed": ["synthetic"]})
        self.assertEqual(result.details, {"trace": [1]})
        with self.assertRaises(FrozenInstanceError):
            result.status = "error"
        report = run_registry(self.registry, Strategy.RANDOM, 11, 1, lambda case, remaining: result,
                              resource_id="fixture", clock=self.clock)
        mutable = report.to_dict()
        mutable["cases"].clear()
        self.assertEqual(len(json.loads(report.to_json())["cases"]), len(self.registry.cases))

    def test_invalid_budget_and_backward_clock_fail_before_misleading_accounting(self):
        for budget in (0, -1, float("inf"), float("nan"), True):
            with self.assertRaises(ValueError):
                self.run_cases(lambda *args: self.fail("invalid budget"), budget=budget)
        clock = iter((100, 99))
        with self.assertRaisesRegex(ValueError, "monotonic"):
            run_registry(self.registry, Strategy.RANDOM, 11, 1, lambda *args: self.fail("bad clock"),
                         resource_id="fixture", clock=lambda: next(clock))


if __name__ == "__main__":
    unittest.main()
