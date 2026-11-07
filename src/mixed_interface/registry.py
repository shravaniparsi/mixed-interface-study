"""Offline, bounded generation from explicit workflow and constraint manifests.

This module does not infer business rules, discover defects, execute an API,
translate a browser form, or infer whether a UI can express an API value. Every
mutation value, expected outcome and provenance statement comes from a manifest.
Version 1 supports route substitution and at most one API payload mutation.
"""

import hashlib
import itertools
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

from .selection import Candidate, DependencyEdge, RouteObligation


class ManifestError(ValueError):
    """The manifest is ambiguous, unsupported, or internally inconsistent."""


class PoolLimitExceeded(ManifestError):
    """The full declared pool exceeds its cap; no partial registry is returned."""


def _json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ManifestError("value must be finite JSON data: {}".format(error)) from error


def _object(value: Any, required: Iterable[str], optional: Iterable[str] = ()) -> Mapping:
    if not isinstance(value, Mapping):
        raise ManifestError("expected an object")
    required, optional = set(required), set(optional)
    missing = required - set(value)
    extra = set(value) - required - optional
    if missing or extra:
        raise ManifestError("object keys: missing={}, unsupported={}".format(sorted(missing), sorted(extra)))
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestError("{} must be a nonempty string".format(name))
    return value


def _id(value: Any, name: str) -> str:
    value = _text(value, name)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise ManifestError("{} must use letters, numbers, underscore, dot or hyphen".format(name))
    return value


def _list(value: Any, name: str) -> list:
    if not isinstance(value, list):
        raise ManifestError("{} must be an array".format(name))
    return value


def _integer(value: Any, name: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ManifestError("{} must be an integer >= {}".format(name, minimum))
    return value


def _interfaces(value: Any, name: str) -> Tuple[str, ...]:
    values = _list(value, name)
    if not values or len(set(values)) != len(values) or any(x not in ("ui", "api") for x in values):
        raise ManifestError("{} must contain distinct ui/api interface names".format(name))
    return tuple(sorted(values))


@dataclass(frozen=True)
class Expectation:
    outcome: str
    category: str
    source: str
    statement: str

    @classmethod
    def parse(cls, raw: Any) -> "Expectation":
        raw = _object(raw, ("outcome", "category", "source", "statement"))
        if raw["outcome"] not in ("accept", "reject", "unknown"):
            raise ManifestError("expectation outcome must be accept, reject or unknown")
        if raw["category"] not in ("contract", "implementation_control", "unresolved"):
            raise ManifestError("expectation category must be contract, implementation_control or unresolved")
        if (raw["outcome"] == "unknown") != (raw["category"] == "unresolved"):
            raise ManifestError("unknown expectations must be unresolved, and unresolved expectations unknown")
        return cls(raw["outcome"], raw["category"], _text(raw["source"], "expectation source"),
                   _text(raw["statement"], "expectation statement"))

    def to_dict(self) -> Dict[str, str]:
        return {"outcome": self.outcome, "category": self.category, "source": self.source, "statement": self.statement}


@dataclass(frozen=True)
class Operation:
    operation_id: str
    interfaces: Tuple[str, ...]
    reference_interface: str
    input_json: str

    @property
    def input(self) -> dict:
        """Return a copy; nested mutable values cannot modify the manifest."""
        return json.loads(self.input_json)

    def to_dict(self) -> dict:
        return {"operation_id": self.operation_id, "interfaces": list(self.interfaces),
                "reference_interface": self.reference_interface, "input": self.input}


@dataclass(frozen=True)
class DeclaredDependency:
    edge: DependencyEdge
    source: str
    statement: str

    def to_dict(self) -> dict:
        return {"producer": self.edge.producer, "consumer": self.edge.consumer,
                "field_or_state": self.edge.field_or_state, "kind": self.edge.kind,
                "evidence": {"source": self.source, "statement": self.statement}}


@dataclass(frozen=True)
class Representation:
    interface: str
    supported: bool
    action: Optional[str] = None
    reason: Optional[str] = None

    def to_dict(self) -> dict:
        if self.supported:
            return {"supported": True, "action": self.action}
        return {"supported": False, "reason": self.reason}


@dataclass(frozen=True)
class Transformation:
    transformation_id: str
    kind: str
    value_json: Optional[str]
    expectation: Expectation
    representations: Tuple[Representation, ...]

    def representation(self, interface: str) -> Representation:
        return next(x for x in self.representations if x.interface == interface)

    def to_dict(self) -> dict:
        result = {"transformation_id": self.transformation_id, "kind": self.kind,
                  "expectation": self.expectation.to_dict(),
                  "representations": {x.interface: x.to_dict() for x in self.representations}}
        if self.kind != "omit":
            result["value"] = json.loads(self.value_json)
        return result


@dataclass(frozen=True)
class Constraint:
    constraint_id: str
    operation_id: str
    input_path: Tuple[str, ...]
    applies_to_interfaces: Tuple[str, ...]
    transformations: Tuple[Transformation, ...]

    def to_dict(self) -> dict:
        return {"constraint_id": self.constraint_id, "operation_id": self.operation_id,
                "input_path": list(self.input_path), "applies_to_interfaces": list(self.applies_to_interfaces),
                "transformations": [x.to_dict() for x in self.transformations]}


@dataclass(frozen=True)
class Bounds:
    max_substitutions: int
    max_mutations: int
    max_cases: int

    def to_dict(self) -> dict:
        return {"max_substitutions": self.max_substitutions, "max_mutations": self.max_mutations, "max_cases": self.max_cases}


@dataclass(frozen=True)
class CostEstimate:
    seconds: float
    source: str
    includes: Tuple[str, ...]

    def to_dict(self) -> dict:
        return {"seconds": self.seconds, "source": self.source, "includes": list(self.includes)}


@dataclass(frozen=True)
class WorkflowManifest:
    manifest_id: str
    operations: Tuple[Operation, ...]
    dependencies: Tuple[DeclaredDependency, ...]
    reference_expectation: Expectation
    constraints: Tuple[Constraint, ...]
    bounds: Bounds
    cost_estimate: CostEstimate
    oracle_json: Optional[str] = None

    def to_dict(self) -> dict:
        result = {"schema_version": 1, "manifest_id": self.manifest_id,
                  "operations": [x.to_dict() for x in self.operations],
                  "dependencies": [x.to_dict() for x in self.dependencies],
                  "reference_expectation": self.reference_expectation.to_dict(),
                  "constraints": [x.to_dict() for x in self.constraints],
                  "bounds": self.bounds.to_dict(), "cost_estimate": self.cost_estimate.to_dict()}
        if self.oracle_json is not None:
            result["oracle"] = json.loads(self.oracle_json)
        return result


def _path_parent(payload: dict, path: Tuple[str, ...]) -> Tuple[dict, str]:
    parent = payload
    for key in path[:-1]:
        if not isinstance(parent, dict) or key not in parent:
            raise ManifestError("input_path must refer to an existing object property")
        parent = parent[key]
    if not isinstance(parent, dict) or path[-1] not in parent:
        raise ManifestError("input_path must refer to an existing object property")
    return parent, path[-1]


def _apply(input_json: str, path: Tuple[str, ...], transformation: Transformation) -> str:
    payload = json.loads(input_json)
    parent, key = _path_parent(payload, path)
    if transformation.kind == "omit":
        del parent[key]
    else:
        parent[key] = json.loads(transformation.value_json)
    return _json(payload)


def parse_manifest(raw: Mapping) -> WorkflowManifest:
    """Validate the v1 schema and detach all data from mutable caller objects.

    Unknown fields are rejected so fault labels or undeclared generation options
    cannot silently enter the selection configuration. Provenance is preserved,
    not verified as true by this parser.
    """
    raw = _object(raw, ("schema_version", "manifest_id", "operations", "dependencies",
                        "reference_expectation", "constraints", "bounds", "cost_estimate"), ("oracle",))
    if raw["schema_version"] != 1 or isinstance(raw["schema_version"], bool):
        raise ManifestError("only schema_version 1 is supported")
    operations = []
    for item in _list(raw["operations"], "operations"):
        item = _object(item, ("operation_id", "interfaces", "reference_interface", "input"))
        interfaces = _interfaces(item["interfaces"], "interfaces")
        if item["reference_interface"] not in interfaces:
            raise ManifestError("reference interface must be supported by its operation")
        if not isinstance(item["input"], dict):
            raise ManifestError("operation input must be a JSON object")
        operations.append(Operation(_id(item["operation_id"], "operation_id"), interfaces,
                                    item["reference_interface"], _json(item["input"])))
    if not operations or len({x.operation_id for x in operations}) != len(operations):
        raise ManifestError("operations must be nonempty with unique operation IDs")
    operation_map = {x.operation_id: x for x in operations}
    position = {x.operation_id: i for i, x in enumerate(operations)}

    dependencies = []
    for item in _list(raw["dependencies"], "dependencies"):
        item = _object(item, ("producer", "consumer", "field_or_state", "kind", "evidence"))
        evidence = _object(item["evidence"], ("source", "statement"))
        edge = DependencyEdge(*(_text(item[x], x) for x in ("producer", "consumer", "field_or_state", "kind")))
        if edge.producer not in operation_map or edge.consumer not in operation_map:
            raise ManifestError("dependency endpoints must be declared operations")
        if position[edge.producer] >= position[edge.consumer]:
            raise ManifestError("dependency producer must precede consumer in the declared workflow")
        dependencies.append(DeclaredDependency(edge, _text(evidence["source"], "dependency source"),
                                              _text(evidence["statement"], "dependency statement")))
    if len({x.edge for x in dependencies}) != len(dependencies):
        raise ManifestError("duplicate dependency edge")
    dependencies.sort(key=lambda x: x.edge)

    constraints = []
    mutation_effects = set()
    for item in _list(raw["constraints"], "constraints"):
        item = _object(item, ("constraint_id", "operation_id", "input_path", "applies_to_interfaces", "transformations"))
        constraint_id = _id(item["constraint_id"], "constraint_id")
        operation_id = _id(item["operation_id"], "constraint operation_id")
        if operation_id not in operation_map:
            raise ManifestError("constraint operation must exist")
        operation = operation_map[operation_id]
        path = tuple(_text(x, "input_path component") for x in _list(item["input_path"], "input_path"))
        if not path:
            raise ManifestError("input_path must be nonempty; v1 supports object-property paths")
        _path_parent(operation.input, path)
        applies = _interfaces(item["applies_to_interfaces"], "applies_to_interfaces")
        if set(applies) - set(operation.interfaces):
            raise ManifestError("mutation interface must be supported by its operation")
        if applies != ("api",):
            raise ManifestError("v1 supports API payload mutations only; UI mutations require an explicit future adapter")
        transformations = []
        for transform in _list(item["transformations"], "transformations"):
            transform = _object(transform, ("transformation_id", "kind", "expectation", "representations"), ("value",))
            kind = transform["kind"]
            if kind not in ("omit", "null", "empty", "boundary", "enum"):
                raise ManifestError("unsupported transformation kind; no implicit/random transformations are generated")
            if kind == "omit":
                if "value" in transform:
                    raise ManifestError("omit must not supply a value")
                value_json = None
            elif kind == "null":
                if transform.get("value") is not None:
                    raise ManifestError("null must have value null")
                value_json = "null"
            else:
                if "value" not in transform:
                    raise ManifestError("{} requires an explicitly declared value".format(kind))
                value = transform["value"]
                if kind == "empty" and not (isinstance(value, (str, list, dict)) and len(value) == 0):
                    raise ManifestError("empty requires an explicit empty string, array or object")
                value_json = _json(value)
            representations_raw = _object(transform["representations"], operation.interfaces)
            representations = []
            for interface in operation.interfaces:
                representation = representations_raw[interface]
                if not isinstance(representation, Mapping) or not isinstance(representation.get("supported"), bool):
                    raise ManifestError("representation.supported must be boolean")
                if representation["supported"]:
                    representation = _object(representation, ("supported", "action"))
                    action = "omit_json_property" if kind == "omit" else "set_json_value"
                    if interface != "api" or representation["action"] != action:
                        raise ManifestError("v1 supported representation must be API {}".format(action))
                    representations.append(Representation(interface, True, action=action))
                else:
                    representation = _object(representation, ("supported", "reason"))
                    representations.append(Representation(interface, False, reason=_text(representation["reason"], "unsupported reason")))
            if not any(x.supported and x.interface in applies for x in representations):
                raise ManifestError("transformation has no supported applicable representation")
            transformation = Transformation(_id(transform["transformation_id"], "transformation_id"), kind,
                                            value_json, Expectation.parse(transform["expectation"]), tuple(representations))
            mutated = _apply(operation.input_json, path, transformation)
            if mutated == operation.input_json:
                raise ManifestError("declared transformation does not change input")
            effect = (operation_id, mutated)
            if effect in mutation_effects:
                raise ManifestError("duplicate mutation effect; consolidate its provenance rather than count identical cases")
            mutation_effects.add(effect)
            transformations.append(transformation)
        if not transformations or len({x.transformation_id for x in transformations}) != len(transformations):
            raise ManifestError("transformations must be nonempty with unique IDs within each constraint")
        constraints.append(Constraint(constraint_id, operation_id, path, applies,
                                      tuple(sorted(transformations, key=lambda x: x.transformation_id))))
    if len({x.constraint_id for x in constraints}) != len(constraints):
        raise ManifestError("duplicate constraint_id")
    constraints.sort(key=lambda x: x.constraint_id)

    bounds_raw = _object(raw["bounds"], ("max_substitutions", "max_mutations", "max_cases"))
    bounds = Bounds(*(_integer(bounds_raw[key], key, minimum) for key, minimum in
                      (("max_substitutions", 0), ("max_mutations", 0), ("max_cases", 1))))
    if bounds.max_substitutions > len(operations):
        raise ManifestError("max_substitutions cannot exceed operation count")
    if bounds.max_mutations > 1:
        raise ManifestError("v1 supports max_mutations 0 or 1 only")
    cost_raw = _object(raw["cost_estimate"], ("seconds", "source", "includes"))
    seconds = cost_raw["seconds"]
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds <= 0:
        raise ManifestError("cost seconds must be finite and positive")
    includes = _list(cost_raw["includes"], "cost includes")
    if set(includes) != {"reset", "operations", "oracle"} or len(includes) != 3:
        raise ManifestError("cost estimate must explicitly include reset, operations and oracle")
    cost = CostEstimate(float(seconds), _text(cost_raw["source"], "cost source"), tuple(sorted(includes)))
    oracle_json = _json(raw["oracle"]) if "oracle" in raw else None
    return WorkflowManifest(_id(raw["manifest_id"], "manifest_id"), tuple(operations), tuple(dependencies),
                            Expectation.parse(raw["reference_expectation"]), tuple(constraints), bounds, cost, oracle_json)


@dataclass(frozen=True)
class CaseOperation:
    operation_id: str
    interface: str
    input_json: str

    def to_dict(self) -> dict:
        return {"operation_id": self.operation_id, "interface": self.interface, "input": json.loads(self.input_json)}


@dataclass(frozen=True)
class GeneratedCase:
    case_id: str
    intervention: str
    operations: Tuple[CaseOperation, ...]
    substitutions: int
    expectation: Expectation
    expectation_operation: Optional[str]
    candidate: Candidate
    mutation_json: Optional[str] = None

    def to_dict(self) -> dict:
        result = {"case_id": self.case_id, "intervention": self.intervention,
                  "operations": [x.to_dict() for x in self.operations], "substitutions": self.substitutions,
                  "expectation": self.expectation.to_dict(),
                  "expectation_scope": {"kind": "operation", "operation_id": self.expectation_operation}
                  if self.expectation_operation else {"kind": "workflow"},
                  "estimated_cost_s": self.candidate.estimated_cost_s,
                  "selection_targets": {
                      "dependencies": [{"producer": e.producer, "consumer": e.consumer,
                                        "field_or_state": e.field_or_state, "kind": e.kind}
                                       for e in sorted(self.candidate.dependencies)],
                      "obligations": [{"producer": o.dependency.producer, "consumer": o.dependency.consumer,
                                       "field_or_state": o.dependency.field_or_state, "kind": o.dependency.kind,
                                       "producer_interface": o.producer_interface, "consumer_interface": o.consumer_interface}
                                      for o in sorted(self.candidate.obligations)],
                  }}
        if self.mutation_json is not None:
            result["mutation"] = json.loads(self.mutation_json)
        return result


@dataclass(frozen=True)
class Exclusion:
    routes: Tuple[Tuple[str, str], ...]
    constraint_id: str
    transformation_id: str
    reason: str

    def to_dict(self) -> dict:
        return {"routes": dict(self.routes), "constraint_id": self.constraint_id,
                "transformation_id": self.transformation_id, "reason": self.reason}


@dataclass(frozen=True)
class CandidateRegistry:
    manifest: WorkflowManifest
    manifest_sha256: str
    cases: Tuple[GeneratedCase, ...]
    exclusions: Tuple[Exclusion, ...]

    @property
    def selection_pool(self) -> Tuple[Candidate, ...]:
        """The selector receives no expectations, provenance or defect labels."""
        return tuple(x.candidate for x in self.cases)

    def to_dict(self) -> dict:
        return {"schema_version": 1, "kind": "offline_declared_candidate_registry",
                "manifest": self.manifest.to_dict(), "manifest_sha256": self.manifest_sha256,
                "case_count": len(self.cases), "cases": [x.to_dict() for x in self.cases],
                "excluded_combinations": [x.to_dict() for x in self.exclusions],
                "semantic_discovery": False,
                "status": "generated_not_executed"}

    def to_json(self, indent: Optional[int] = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent, allow_nan=False) + "\n"


def _routes(manifest: WorkflowManifest):
    reference = tuple(x.reference_interface for x in manifest.operations)
    yield reference, 0
    switchable = [i for i, x in enumerate(manifest.operations) if len(x.interfaces) > 1]
    for count in range(1, min(manifest.bounds.max_substitutions, len(switchable)) + 1):
        for indices in itertools.combinations(switchable, count):
            alternatives = [tuple(x for x in manifest.operations[i].interfaces if x != reference[i]) for i in indices]
            for replacements in itertools.product(*alternatives):
                route = list(reference)
                for i, replacement in zip(indices, replacements):
                    route[i] = replacement
                yield tuple(route), count


def generate_registry(raw: Mapping) -> CandidateRegistry:
    """Return the complete bounded pool, or fail rather than silently truncate.

    Route-only cases use the declared full inputs. Payload cases vary one
    declared object property on a supported API operation. All targets remain
    prospective until the runner submits observed ExecutionFeedback.
    """
    manifest = parse_manifest(raw)
    manifest_sha = hashlib.sha256(_json(manifest.to_dict()).encode()).hexdigest()
    cases, exclusions = [], []
    dependencies = frozenset(x.edge for x in manifest.dependencies)

    def add_case(route, count, constraint=None, transformation=None):
        if len(cases) >= manifest.bounds.max_cases:
            raise PoolLimitExceeded("complete candidate pool exceeds max_cases={}; increase the declared cap or reduce bounds".format(manifest.bounds.max_cases))
        routes = {op.operation_id: interface for op, interface in zip(manifest.operations, route)}
        operations = []
        for op, interface in zip(manifest.operations, route):
            payload = op.input_json
            if constraint is not None and op.operation_id == constraint.operation_id:
                payload = _apply(payload, constraint.input_path, transformation)
            operations.append(CaseOperation(op.operation_id, interface, payload))
        mutation = None
        intervention = "route_only" if constraint is None else "payload_mutation"
        if constraint is not None:
            mutation = {"constraint_id": constraint.constraint_id,
                        "transformation_id": transformation.transformation_id,
                        "operation_id": constraint.operation_id, "input_path": list(constraint.input_path),
                        "kind": transformation.kind,
                        "representation": transformation.representation(routes[constraint.operation_id]).to_dict()}
        identity = {"manifest_id": manifest.manifest_id, "intervention": intervention,
                    "operations": [x.to_dict() for x in operations], "mutation": mutation}
        digest = hashlib.sha256(_json(identity).encode()).hexdigest()[:24]
        case_id = "{}::{}::{}".format(manifest.manifest_id, intervention.replace("_", "-"), digest)
        obligations = frozenset(RouteObligation(edge, routes[edge.producer], routes[edge.consumer]) for edge in dependencies)
        candidate = Candidate(case_id, dependencies, obligations, manifest.cost_estimate.seconds)
        cases.append(GeneratedCase(case_id, intervention, tuple(operations), count,
                                   transformation.expectation if transformation else manifest.reference_expectation,
                                   constraint.operation_id if constraint else None, candidate,
                                   _json(mutation) if mutation else None))

    for route, count in _routes(manifest):
        add_case(route, count)
        if manifest.bounds.max_mutations == 0:
            continue
        route_map = tuple((op.operation_id, interface) for op, interface in zip(manifest.operations, route))
        by_operation = dict(route_map)
        for constraint in manifest.constraints:
            interface = by_operation[constraint.operation_id]
            for transformation in constraint.transformations:
                representation = transformation.representation(interface)
                if interface not in constraint.applies_to_interfaces or not representation.supported:
                    reason = representation.reason or "Interface excluded by applies_to_interfaces."
                    exclusions.append(Exclusion(route_map, constraint.constraint_id, transformation.transformation_id, reason))
                    continue
                add_case(route, count, constraint, transformation)
    return CandidateRegistry(manifest, manifest_sha, tuple(cases), tuple(exclusions))
