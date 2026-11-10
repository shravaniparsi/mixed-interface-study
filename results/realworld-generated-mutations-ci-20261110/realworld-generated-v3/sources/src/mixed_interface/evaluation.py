"""Pair declared candidates and verify content-addressed preparation records.

Pairing establishes equal registered inputs, not equivalent implemented oracles.
No function in this module authorizes execution or assigns a defect label.
"""
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def generated_pairs(pool, catalog, workflow, exposure):
    """Pair only consumer-interface changes; all declared semantic inputs agree."""
    groups = defaultdict(list)
    seen = set()
    for case in pool["cases"]:
        if case["case_id"] in seen:
            raise ValueError("Duplicate generated case ID")
        seen.add(case["case_id"])
        operations = case["operations"]
        if len(operations) != 2 or operations[1]["interface"] not in {"api", "ui"}:
            raise ValueError("Expected two-operation API/UI continuation candidate")
        key = {
            "producer": operations[0],
            "consumer": {k: v for k, v in operations[1].items() if k != "interface"},
            "intervention": case["intervention"],
            "mutation": case.get("mutation"),
            "expectation": case["expectation"],
            "expectation_scope": case.get("expectation_scope"),
        }
        groups[canonical(key)].append(case)
    pairs = []
    for encoded, cases in groups.items():
        interfaces = [c["operations"][1]["interface"] for c in cases]
        if sorted(interfaces) != ["api", "ui"]:
            raise ValueError("Unpaired or duplicate continuation for a declared prefix")
        key = json.loads(encoded)
        pairs.append({
            "pair_id": catalog + "::" + digest(key)[:24],
            "catalog": catalog,
            "workflow_id": workflow,
            "producer_interface": key["producer"]["interface"],
            "registered_semantics_sha256": digest(key),
            "case_ids": {c["operations"][1]["interface"]: c["case_id"] for c in cases},
            "intervention": key["intervention"],
            "mutation": key["mutation"],
            "prior_exposure": exposure[key["intervention"]],
            "pair_basis": "equal_registered_producer_and_intended_consumer_inputs",
            "implemented_oracle_equivalence_established": False,
        })
    return pairs


def legacy_pairs(registry, catalog, workflow_map, *, petclinic=False):
    if petclinic and sorted(registry.get("oracles", [])) != ["api_semantic", "fresh_ui"]:
        raise ValueError("PetClinic registry must explicitly declare both continuation oracles")
    pairs, singletons, seen = [], [], set()
    for case in registry["candidates" if petclinic else "cases"]:
        identifier = case["id" if petclinic else "candidate_id"]
        if identifier in seen:
            raise ValueError("Duplicate legacy candidate ID")
        seen.add(identifier)
        continuations = ["api", "ui"] if petclinic else case["continuations"]
        if not continuations or len(continuations) != len(set(continuations)) or not set(continuations) <= {"api", "ui"}:
            raise ValueError("Invalid legacy continuation list")
        row = {
            "pair_id": catalog + "::" + identifier,
            "catalog": catalog,
            "candidate_id": identifier,
            "workflow_id": workflow_map[case["template" if petclinic else "workflow"]],
            "producer_interface": "api" if petclinic else case["prefix_interface"],
            "registered_semantics_sha256": digest(case),
            "continuations": continuations,
            "prior_exposure": "examined_development_candidate",
            "pair_basis": "declared_same_prefix_candidate_with_independent_replays",
            "implemented_oracle_equivalence_established": False,
        }
        (pairs if set(continuations) == {"api", "ui"} else singletons).append(row)
    return pairs, singletons


def file_hashes(root, paths):
    root = Path(root).resolve()
    result = {}
    for name in sorted(set(paths)):
        path = (root / name).resolve()
        if path == root or root not in path.parents or not path.is_file():
            raise ValueError("Artifact must be an existing file inside the study: " + name)
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def verify_snapshot(root, snapshot, required_paths):
    recorded = snapshot["artifact_sha256"]
    if not recorded:
        raise ValueError("Empty artifact inventory")
    if set(recorded) != set(required_paths):
        raise ValueError("Snapshot must cover the complete required artifact inventory")
    observed = file_hashes(root, recorded)
    changed = sorted(k for k in recorded if recorded[k] != observed[k])
    if changed:
        raise ValueError("Snapshot artifact changed: " + ", ".join(changed))
    if snapshot["primary_freeze_complete"]:
        raise ValueError("This preparation schema cannot represent a completed primary freeze")
    if snapshot["execution_authorized_by_snapshot"]:
        raise ValueError("A preparation snapshot cannot authorize an experiment")
    return True
