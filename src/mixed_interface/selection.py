"""Finite-pool selection with explicit, observed coverage feedback.

All strategies accept the same immutable candidates. Generic selection counts
producer/consumer edges; route selection distinguishes the interfaces at both
ends. Neither consumes defect labels. Costs are supplied by the runner.
This is an unvalidated research prototype, not a reproduction of RESTler.
"""

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import FrozenSet, Iterable, List, Optional, Set, Tuple


def _nonempty(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("{} must be a nonempty string".format(name))


@dataclass(frozen=True, order=True)
class DependencyEdge:
    """A field or state produced by one operation and consumed by another."""
    producer: str
    consumer: str
    field_or_state: str
    kind: str = "data"

    def __post_init__(self) -> None:
        for name in ("producer", "consumer", "field_or_state", "kind"):
            _nonempty(getattr(self, name), name)


@dataclass(frozen=True, order=True)
class RouteObligation:
    """An edge exercised through specific producer and consumer interfaces."""
    dependency: DependencyEdge
    producer_interface: str
    consumer_interface: str

    def __post_init__(self) -> None:
        if not isinstance(self.dependency, DependencyEdge):
            raise TypeError("dependency must be a DependencyEdge")
        for name in ("producer_interface", "consumer_interface"):
            if getattr(self, name) not in ("ui", "api"):
                raise ValueError("{} must be 'ui' or 'api'".format(name))


@dataclass(frozen=True)
class Candidate:
    """Declared targets before execution; selection does not count as coverage.

    Estimated cost includes the protocol's reset and continuation costs.
    Distinct payloads can share targets but must have different case IDs.
    """
    case_id: str
    dependencies: FrozenSet[DependencyEdge]
    obligations: FrozenSet[RouteObligation]
    estimated_cost_s: float

    def __post_init__(self) -> None:
        _nonempty(self.case_id, "case_id")
        object.__setattr__(self, "dependencies", frozenset(self.dependencies))
        object.__setattr__(self, "obligations", frozenset(self.obligations))
        if not all(isinstance(x, DependencyEdge) for x in self.dependencies):
            raise TypeError("dependencies must contain DependencyEdge values")
        if not all(isinstance(x, RouteObligation) for x in self.obligations):
            raise TypeError("obligations must contain RouteObligation values")
        if any(x.dependency not in self.dependencies for x in self.obligations):
            raise ValueError("each obligation must refer to a declared dependency")
        if isinstance(self.estimated_cost_s, bool):
            raise ValueError("estimated_cost_s must be a finite positive number")
        try:
            cost = float(self.estimated_cost_s)
        except (ValueError, TypeError):
            raise ValueError("estimated_cost_s must be a finite positive number")
        if not math.isfinite(cost) or cost <= 0:
            raise ValueError("estimated_cost_s must be a finite positive number")
        object.__setattr__(self, "estimated_cost_s", cost)


@dataclass(frozen=True)
class ExecutionFeedback:
    """Observed coverage, not predictions based merely on reached operations.

    The runner must explicitly report exercised fields/states, and retain trace
    evidence of consumption. Every reported edge must have reached both ends.
    """
    case_id: str
    reached_operations: FrozenSet[str]
    exercised_dependencies: FrozenSet[DependencyEdge] = field(default_factory=frozenset)
    exercised_obligations: FrozenSet[RouteObligation] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        _nonempty(self.case_id, "case_id")
        for name in ("reached_operations", "exercised_dependencies", "exercised_obligations"):
            object.__setattr__(self, name, frozenset(getattr(self, name)))
        for operation in self.reached_operations:
            _nonempty(operation, "reached operation")
        if not all(isinstance(x, DependencyEdge) for x in self.exercised_dependencies):
            raise TypeError("exercised_dependencies must contain DependencyEdge values")
        if not all(isinstance(x, RouteObligation) for x in self.exercised_obligations):
            raise TypeError("exercised_obligations must contain RouteObligation values")
        edges = self.exercised_dependencies | frozenset(x.dependency for x in self.exercised_obligations)
        for edge in edges:
            if {edge.producer, edge.consumer} - self.reached_operations:
                raise ValueError("reported coverage requires both endpoints to be reached")


class Strategy(str, Enum):
    RANDOM = "random"
    DEPENDENCY_GREEDY = "dependency_greedy"
    ROUTE_GREEDY = "route_greedy"


@dataclass(frozen=True)
class SelectionDecision:
    case_id: str
    strategy: Strategy
    marginal_targets: Optional[int]
    estimated_cost_s: float
    targets_per_second: Optional[float]


class CandidateSelector:
    """Select each case at most once; update coverage only from feedback.

    Greedy scores are uncovered targets per estimated second. Seeded ties use
    sorted case IDs so input iteration order cannot influence the selection.
    Zero-marginal cases remain eligible. The runner enforces wall-clock budgets.
    """
    def __init__(self, candidates: Iterable[Candidate], strategy: Strategy, seed: int = 0):
        self.strategy = Strategy(strategy)
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError("seed must be an integer")
        self.seed = seed
        self._rng = random.Random(seed)
        self._candidates = {}
        for candidate in candidates:
            if not isinstance(candidate, Candidate):
                raise TypeError("candidates must contain Candidate values")
            if candidate.case_id in self._candidates:
                raise ValueError("duplicate case_id: {}".format(candidate.case_id))
            self._candidates[candidate.case_id] = candidate
        self._remaining: Set[str] = set(self._candidates)
        self._selected: Set[str] = set()
        self._observed: Set[str] = set()
        self._covered_dependencies: Set[DependencyEdge] = set()
        self._covered_obligations: Set[RouteObligation] = set()
        self._decisions: List[SelectionDecision] = []

    @property
    def candidate_ids(self) -> Tuple[str, ...]:
        return tuple(sorted(self._candidates))

    @property
    def remaining_ids(self) -> Tuple[str, ...]:
        return tuple(sorted(self._remaining))

    @property
    def exhausted(self) -> bool:
        return not self._remaining

    @property
    def covered_dependencies(self) -> FrozenSet[DependencyEdge]:
        return frozenset(self._covered_dependencies)

    @property
    def covered_obligations(self) -> FrozenSet[RouteObligation]:
        return frozenset(self._covered_obligations)

    @property
    def decisions(self) -> Tuple[SelectionDecision, ...]:
        return tuple(self._decisions)

    def _marginal(self, candidate: Candidate) -> int:
        if self.strategy == Strategy.DEPENDENCY_GREEDY:
            return len(candidate.dependencies - self._covered_dependencies)
        return len(candidate.obligations - self._covered_obligations)

    def select_next(self) -> Optional[Candidate]:
        if self.exhausted:
            return None
        available = [self._candidates[x] for x in sorted(self._remaining)]
        marginal = None
        score = None
        if self.strategy == Strategy.RANDOM:
            selected = self._rng.choice(available)
        else:
            # Compare exact ratios of supplied decimal costs for stable ties.
            scores = [Fraction(self._marginal(c)) / Fraction(str(c.estimated_cost_s)) for c in available]
            best = max(scores)
            selected = self._rng.choice([c for c, s in zip(available, scores) if s == best])
            marginal = self._marginal(selected)
            score = float(best)
        self._remaining.remove(selected.case_id)
        self._selected.add(selected.case_id)
        self._decisions.append(SelectionDecision(
            selected.case_id, self.strategy, marginal, selected.estimated_cost_s, score
        ))
        return selected

    def record_feedback(self, feedback: ExecutionFeedback) -> None:
        if not isinstance(feedback, ExecutionFeedback):
            raise TypeError("feedback must be ExecutionFeedback")
        if feedback.case_id not in self._selected:
            raise ValueError("feedback requires a previously selected case")
        if feedback.case_id in self._observed:
            raise ValueError("feedback has already been recorded for this case")
        candidate = self._candidates[feedback.case_id]
        if feedback.exercised_dependencies - candidate.dependencies:
            raise ValueError("feedback contains an undeclared dependency")
        if feedback.exercised_obligations - candidate.obligations:
            raise ValueError("feedback contains an undeclared route obligation")
        self._covered_dependencies.update(feedback.exercised_dependencies)
        self._covered_dependencies.update(x.dependency for x in feedback.exercised_obligations)
        self._covered_obligations.update(feedback.exercised_obligations)
        self._observed.add(feedback.case_id)
