#!/usr/bin/env python3
"""Register existing candidate pairs and hash the evaluation preparation package."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mixed_interface.evaluation import generated_pairs, legacy_pairs, file_hashes, verify_snapshot

WORKFLOWS = {
    "article-create-edit": "realworld.article_create_body_edit",
    "article-update-comment": "realworld.article_update_comment_create",
    "comment-create-delete": "realworld.comment_create_delete",
    "profile-update-edit": "realworld.profile_update_settings_edit",
    "owner_address_edit": "petclinic.owner_create_address_edit",
    "pet_rename": "petclinic.pet_create_rename",
    "visit_reschedule": "petclinic.visit_create_reschedule",
    "quartz": "quartz.stored_job_create_description_edit",
}
SOURCES = {
    "realworld_development": "manifests/realworld-boundary-registry-v1.json",
    "petclinic_development": "manifests/petclinic-candidates-v1.json",
    "realworld_generated_integration": "manifests/realworld-article-generated-pool-v1.json",
    "quartz_generated_v2": "manifests/quartz-job-generated-pool-v2.json",
}
ARTIFACTS = [
    'scripts/build_control_analysis.py',
    'scripts/summarize_petclinic_integrity_components.py',
    'src/mixed_interface/attribution.py',
    'tests/test_attribution.py',
    'tests/test_petclinic_integrity_components.py',
    'manifests/component-attribution-v1.json',
    'manifests/unified-control-inputs-v1.json',
    'protocol/unified-control-analysis-v1.md',
    'results/unified-controls-20261107/analysis.json',
    'results/unified-controls-20261107/petclinic-components.json',
    "manifests/petclinic-execution-integrity.json",
    "results/petclinic-integrity-ci-20261107/verification.json",
    "results/petclinic-integrity-ci-20261107/petclinic-integrity-validation.json",
    "scripts/petclinic_integrity.mjs", "scripts/petclinic_cleanup.mjs", "scripts/petclinic_response_capture.mjs",
    "scripts/validate_petclinic_integrity.py", "scripts/ci/prepare_petclinic.py", "scripts/ci/run_petclinic_integrity.py",
    "tests/petclinic_integrity.test.mjs", "tests/petclinic_cleanup.test.mjs", "tests/petclinic_capture.test.mjs",
    "tests/test_petclinic_integrity.py", "tests/fixtures/petclinic_boundary_adapter.mjs",
    "protocol/petclinic-integrity-validation-v1.md", "manifests/petclinic-integrity-controls-v1.json",
    "manifests/realworld-execution-integrity.json",
    "results/realworld-integrity-ci-20261107/verification.json",
    "results/realworld-integrity-ci-20261107/integrity-validation-summary.json",
    "scripts/realworld_integrity.mjs", "tests/realworld_integrity.test.mjs",
    "tests/test_realworld_integrity.py", "tests/fixtures/realworld_capture_adapter.mjs",
    "scripts/validate_realworld_integrity.py", "protocol/realworld-integrity-validation-v1.md",
    "manifests/realworld-integrity-controls-v1.json",
    *SOURCES.values(),
    "manifests/multiworkflow-eligibility-v1.json",
    "manifests/paired-candidate-inventory-v1.json",
    "protocol/paired-oracle-analysis-v1.md",
    "protocol/paired-control-validation-v1.md",
    "protocol/multiworkflow-freeze-gates-v1.md",
    "protocol/pilot-v0.2.md",
    "protocol/runtime-integration-v1.md",
    "protocol/ci-portability-v1.md",
    "manifests/realworld.json", "manifests/petclinic.json",
    "manifests/petclinic-reproducibility.json",
    "manifests/petclinic-source-adjudication.json",
    "manifests/realworld-python-lock.txt",
    "manifests/quartz-artifact-lock.json",
    "manifests/quartz-declared-dependencies.json",
    "manifests/quartz-generated-adapter-validation.json",
    "manifests/quartz-paired-control-validation.json",
    "results/quartz-paired-controls-ci-20261107/summary.json",
    "results/quartz-paired-controls-ci-20261107/verification.json",
    "manifests/quartz-source-mapping.json",
    "manifests/realworld-article-generation-v1.json",
    "manifests/quartz-job-generation-v2.json",
    "scripts/realworld_boundary_case.mjs", "scripts/run_realworld_boundaries.py",
    "scripts/petclinic_boundary_slice.mjs",
    "scripts/realworld_generated_case.mjs", "scripts/realworld_case_worker.py",
    "scripts/run_generated_integration.py",
    "scripts/quartz_generated_case.mjs", "scripts/run_quartz_registry.mjs",
    "scripts/quartz_browser_cleanup.py",
    "scripts/summarize_quartz_oracle_components.py",
    "scripts/summarize_realworld_oracle_components.py",
    "scripts/summarize_petclinic_oracle_components.py",
    "scripts/run_quartz_pairs.py",
    "scripts/response_capture.mjs", "tests/response_capture.test.mjs",
    "scripts/validate_realworld_capture.py", "protocol/realworld-capture-validation-v1.md",
    "manifests/realworld-capture-repair.json",
    "results/realworld-capture-ci-20261107/capture-validation-summary.json",
    "results/realworld-capture-ci-20261107/verification.json",
    "results/realworld-capture-ci-20261107/historical-regression.json",
    "scripts/prepare_evaluation.py", "src/mixed_interface/evaluation.py",
    "tests/test_evaluation.py", "tests/test_quartz_oracle_components.py",
    "tests/test_realworld_oracle_components.py", "tests/test_petclinic_oracle_components.py",
    "tests/test_quartz_pairs.py", "tests/quartz_generated_case.test.mjs",
    "src/mixed_interface/registry.py", "src/mixed_interface/runtime.py",
    "src/mixed_interface/selection.py",
    "scripts/ci/prepare_quartz.py", "scripts/ci/prepare_realworld.py",
    "scripts/ci/capture_versions.py", "scripts/ci/package.json",
    "scripts/ci/browser_info.mjs", "scripts/ci/install_browser.sh",
    "scripts/ci/run_applications.sh", ".github/workflows/applications.yml", ".github/workflows/unit.yml",
]


def load(path):
    return json.loads((ROOT / path).read_text())


def inventory():
    pairs, singletons = [], []
    for catalog in ("realworld_development", "petclinic_development"):
        found, unpaired = legacy_pairs(load(SOURCES[catalog]), catalog, WORKFLOWS,
                                      petclinic=catalog.startswith("petclinic"))
        pairs.extend(found)
        singletons.extend(unpaired)
    pairs.extend(generated_pairs(
        load(SOURCES["realworld_generated_integration"]), "realworld_generated_integration",
        WORKFLOWS["article-create-edit"],
        {"route_only": "examined_engineering_control", "payload_mutation": "examined_engineering_candidate"}))
    pairs.extend(generated_pairs(
        load(SOURCES["quartz_generated_v2"]), "quartz_generated_v2", WORKFLOWS["quartz"],
        {"route_only": "examined_source_inspected_control", "payload_mutation": "source_inspected_boundary_not_executed"}))
    assert len({p["pair_id"] for p in pairs}) == len(pairs)
    return {
        "schema_version": 1, "kind": "declared_candidate_pair_inventory",
        "primary_freeze_complete": False,
        "source_sha256": file_hashes(ROOT, SOURCES.values()),
        "pair_entries": len(pairs), "singleton_control_entries": len(singletons),
        "by_catalog": dict(Counter(p["catalog"] for p in pairs)),
        "workflow_templates": len({p["workflow_id"] for p in pairs}),
        "independent_sample_size": None,
        "interpretation": "Catalog entries overlap across development and engineering strata; do not pool them as independent samples. Pairing registers intent, not implemented-oracle equivalence.",
        "pairs": pairs, "unpaired_controls": singletons,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Verify the saved preparation hashes without rewriting")
    args = parser.parse_args()
    snapshot_path = ROOT / "manifests/evaluation-preparation-v1.json"
    if args.verify:
        verify_snapshot(ROOT, json.loads(snapshot_path.read_text()), ARTIFACTS)
        saved = load("manifests/paired-candidate-inventory-v1.json")
        if saved != inventory():
            raise ValueError("Saved candidate pairing does not match current registries")
        print("Preparation hashes and declared pairs verified; primary freeze remains incomplete.")
        return
    ledger = load("manifests/multiworkflow-eligibility-v1.json")
    if {row["workflow_id"] for row in ledger["workflows"]} != set(WORKFLOWS.values()):
        raise ValueError("Ledger must account for all eight inventoried templates")
    value = inventory()
    (ROOT / "manifests/paired-candidate-inventory-v1.json").write_text(json.dumps(value, indent=2) + "\n")
    snapshot = {
        "schema_version": 1, "kind": "evaluation_preparation_snapshot",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "primary_freeze_complete": False, "execution_authorized_by_snapshot": False,
        "workflow_templates": len(ledger["workflows"]), "declared_pair_entries": value["pair_entries"],
        "unpaired_control_entries": value["singleton_control_entries"],
        "gate_status": ledger["gate_status"], "blocking_items": ledger["blocking_items"],
        "artifact_sha256": file_hashes(ROOT, ARTIFACTS),
        "scope": "A dated reproducible preparation snapshot. It cannot be relabelled as a completed primary freeze or used to dispatch unexecuted boundaries.",
    }
    verify_snapshot(ROOT, snapshot, ARTIFACTS)
    snapshot_path.write_text(json.dumps(snapshot, indent=2) + "\n")
    print(json.dumps({k: snapshot[k] for k in ["recorded_at_utc", "workflow_templates", "declared_pair_entries", "unpaired_control_entries", "primary_freeze_complete"]}, indent=2))


if __name__ == "__main__":
    main()
