"""Budget accounting for a finite, immutable generated case pool.

The controller cannot preempt an arbitrary Python callback. The callback MUST
enforce its supplied timeout on an external process (including descendants),
and return only after per-case reset, startup, actions, oracle and teardown.
OS termination/cleanup can overrun a deadline; actual overruns are recorded,
not described as strict elapsed-time guarantees. Late feedback earns no credit.

Fixed common host setup and immutable configuration hashing precede the budget.
Callers must retain identical comparison-context hashes across strategies.
Per-case work and selection overhead are inside the monotonic wall-clock budget.
Estimated costs affect selector ranking only, never elapsed-time accounting.
Final report serialization is outside the measured execution interval.
"""

import hashlib
import json
import math
import time
from dataclasses import dataclass
from typing import Callable, Optional

from .registry import CandidateRegistry
from .selection import CandidateSelector, ExecutionFeedback, Strategy


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _obligations(items):
    return [{"dependency": vars(item.dependency), "producer_interface": item.producer_interface,
             "consumer_interface": item.consumer_interface} for item in sorted(items)]


def _feedback(feedback):
    if feedback is None:
        return None
    return {
        "case_id": feedback.case_id,
        "reached_operations": sorted(feedback.reached_operations),
        "exercised_dependencies": [vars(edge) for edge in sorted(feedback.exercised_dependencies)],
        "exercised_obligations": _obligations(feedback.exercised_obligations),
    }


class ExecutionCancelled(Exception):
    """An adapter may raise this after cancelling and cleaning up its child."""


@dataclass(frozen=True, init=False)
class CaseExecution:
    """Adapter result; outcome/details are copied as finite JSON data.

    Completed means the adapter finished, not that an application oracle passed.
    Classify that observation in outcome. Only completed, timely results may
    contribute explicit feedback; other statuses stop this run.
    """
    status: str
    outcome_json: str
    feedback: Optional[ExecutionFeedback]
    details_json: str

    def __init__(self, status, outcome, feedback=None, details=None):
        if status not in ("completed", "timeout", "cancelled", "error"):
            raise ValueError("status must be completed, timeout, cancelled or error")
        if feedback is not None and not isinstance(feedback, ExecutionFeedback):
            raise TypeError("feedback must be ExecutionFeedback or None")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "outcome_json", _json(outcome))
        object.__setattr__(self, "feedback", feedback)
        object.__setattr__(self, "details_json", _json(details))

    @property
    def outcome(self):
        return json.loads(self.outcome_json)

    @property
    def details(self):
        return json.loads(self.details_json)


@dataclass(frozen=True)
class RunRecord:
    """Immutable JSON report; to_dict returns a detached mutable copy."""
    report_json: str

    def to_dict(self):
        return json.loads(self.report_json)

    def to_json(self, indent=2):
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent, allow_nan=False) + "\n"


def run_registry(registry: CandidateRegistry, strategy: Strategy, seed: int,
                 budget_s: float, execute_case: Callable, *, resource_id: str,
                 setup_metadata=None, resource_metadata=None,
                 cancel_requested=None, clock=time.monotonic) -> RunRecord:
    """Run execute_case(GeneratedCase, remaining_seconds) -> CaseExecution.

    The remaining allowance is measured immediately before callback invocation.
    Selection is checked again against deadline/cancellation before invocation.
    No reservation based on an estimated cost is treated as completed work.
    A selected case that cannot start is recorded with status=not_started.

    The callback owns process-group timeout enforcement and cleanup. Cancellation
    polling here occurs between cases; interrupting an active child belongs to
    the callback. setup_metadata describes fixed common work outside the budget;
    resource_metadata identifies the actual fixture, versions and environment.
    Metadata is descriptive, not independent verification of those resources.
    """
    if not isinstance(registry, CandidateRegistry):
        raise TypeError("registry must be CandidateRegistry")
    if isinstance(budget_s, bool) or not isinstance(budget_s, (int, float)) or not math.isfinite(budget_s) or budget_s <= 0:
        raise ValueError("budget_s must be finite and positive")
    if not isinstance(resource_id, str) or not resource_id.strip():
        raise ValueError("resource_id must be nonempty")
    if not callable(execute_case) or not callable(clock):
        raise TypeError("execute_case and clock must be callable")
    if cancel_requested is not None and not callable(cancel_requested):
        raise TypeError("cancel_requested must be callable")
    strategy = Strategy(strategy)
    selector = CandidateSelector(registry.selection_pool, strategy, seed)
    by_id = {case.case_id: case for case in registry.cases}
    pool = [case.to_dict() for case in registry.cases]
    resources = json.loads(_json({"resource_id": resource_id, "metadata": resource_metadata}))
    setup = json.loads(_json(setup_metadata))
    hashes = {"manifest_sha256": registry.manifest_sha256,
              "effective_pool_sha256": _hash(pool),
              "oracle_sha256": _hash(json.loads(registry.manifest.oracle_json) if registry.manifest.oracle_json else None),
              "resources_sha256": _hash(resources), "setup_sha256": _hash(setup)}
    hashes["comparison_context_sha256"] = _hash({"hashes": hashes, "budget_s": float(budget_s)})
    exclusions = [item.to_dict() for item in registry.exclusions]
    cancelled = cancel_requested or (lambda: False)
    previous = None

    def now():
        nonlocal previous
        value = clock()
        if not isinstance(value, (int, float)) or not math.isfinite(value) or (previous is not None and value < previous):
            raise ValueError("clock must return finite monotonic values")
        previous = value
        return value

    started = now()
    deadline = started + budget_s
    records = []
    while True:
        cancel_before_selection = cancelled()
        tick = now()
        if cancel_before_selection:
            stop_reason = "cancelled"
            break
        if tick >= deadline:
            stop_reason = "budget_exhausted"
            break
        if selector.exhausted:
            stop_reason = "pool_exhausted"
            break
        candidate = selector.select_next()
        decision = selector.decisions[-1]
        cancel_before_start = cancelled()
        record = {"case_id": candidate.case_id, "selection_index": len(records),
                  "estimated_cost_s": candidate.estimated_cost_s,
                  "marginal_targets_at_selection": decision.marginal_targets,
                  "started_elapsed_s": None, "ended_elapsed_s": None,
                  "allocated_remaining_s": None, "actual_cost_s": 0.0,
                  "status": "not_started", "callback_status": None,
                  "failure_classification": None, "outcome": None, "details": None,
                  "feedback": None, "feedback_credited": False}
        case_started = now()
        remaining = max(0.0, deadline - case_started)
        record.update(ended_elapsed_s=case_started - started, allocated_remaining_s=remaining)
        if cancel_before_start or remaining <= 0:
            record["failure_classification"] = "cancelled_before_start" if cancel_before_start else "deadline_before_start"
            records.append(record)
            stop_reason = "cancelled" if cancel_before_start else "budget_exhausted"
            break
        record["started_elapsed_s"] = case_started - started
        failure = None
        try:
            result = execute_case(by_id[candidate.case_id], remaining)
            if not isinstance(result, CaseExecution):
                failure = "invalid_callback_result"
                result = CaseExecution("error", None)
        except TimeoutError:
            result, failure = CaseExecution("timeout", None), "callback_timeout"
        except ExecutionCancelled:
            result, failure = CaseExecution("cancelled", None), "callback_cancelled"
        except Exception as error:
            result = CaseExecution("error", None, details={"exception_type": type(error).__name__})
            failure = "callback_exception"
        case_ended = now()
        record.update(status=result.status, callback_status=result.status,
                      ended_elapsed_s=case_ended - started, actual_cost_s=case_ended - case_started,
                      outcome=result.outcome, details=result.details, feedback=_feedback(result.feedback))
        if case_ended > deadline:
            record.update(status="timeout", failure_classification="deadline_overrun")
        elif result.status != "completed":
            record["failure_classification"] = failure or "adapter_" + result.status
        elif result.feedback is not None:
            try:
                if result.feedback.case_id != candidate.case_id:
                    raise ValueError("feedback case differs from invoked case")
                operations = {item.operation_id for item in by_id[candidate.case_id].operations}
                if result.feedback.reached_operations - operations:
                    raise ValueError("feedback includes an undeclared operation")
                selector.record_feedback(result.feedback)
                record["feedback_credited"] = True
            except (TypeError, ValueError) as error:
                record.update(status="error", failure_classification="invalid_feedback",
                              feedback_error=str(error))
        records.append(record)
        if record["status"] != "completed":
            stop_reason = {"timeout": "case_timeout", "cancelled": "cancelled", "error": "execution_error"}[record["status"]]
            break
    elapsed = now() - started
    report = {
        "schema_version": 1, "kind": "budgeted_registry_run", "strategy": strategy.value,
        "seed": seed, "budget_s": float(budget_s), "elapsed_s": elapsed,
        "deadline_overrun_s": max(0.0, elapsed - budget_s), "stop_reason": stop_reason,
        "registered_case_count": len(registry.cases), "hashes": hashes,
        "resources": resources, "fixed_common_setup": {"budget_scope": "outside", "metadata": setup},
        "budget_policy": {"clock": "monotonic", "per_case_scope": ["reset", "startup", "actions", "oracle", "teardown"],
                          "selection_overhead": "inside", "estimates_are_measurements": False,
                          "timeout_enforcement": "external_process_callback_contract",
                          "controller_can_preempt_callback": False,
                          "cleanup_overruns_recorded": True, "late_feedback_credited": False},
        "selection_order": [item["case_id"] for item in records],
        "execution_order": [item["case_id"] for item in records if item["started_elapsed_s"] is not None],
        "remaining_case_ids": list(selector.remaining_ids), "cases": records,
        "excluded_combinations": exclusions,
        "observed_coverage": {"dependencies": [vars(edge) for edge in sorted(selector.covered_dependencies)],
                              "obligations": _obligations(selector.covered_obligations)},
    }
    return RunRecord(_json(report))
