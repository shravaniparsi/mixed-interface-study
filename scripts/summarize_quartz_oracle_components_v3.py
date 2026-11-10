#!/usr/bin/env python3
"""Attribute recorded Quartz checks without executing the application.

This reducer reports source-check observations, never defects or root causes.
The supplementary final UI read remains separate even on an API-consumer route.
Only the pinned adapter's explicit check vocabulary is accepted. Unfinished,
unknown or structurally missing evidence cannot yield a clean comparison.

Usage: python3 scripts/summarize_quartz_oracle_components.py RUN_DIRECTORY
Output is JSON on stdout; input files are never modified. Exit 1 means evidence
is incomplete/invalid, not that a recorded application check failed.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


ADAPTER_SHA256 = "366a1c21a9e136aa31302d38c0d26223d714418b48b99d29487c637c2421dd92"
REGISTRY_SHA256 = "fd575f01818659c1efde48514392b8cba8b06812f3e385049314edfcae58d2e0"
JOB_PATH = "/quartz-manager/jobs/RESEARCH/pilot-job"
COMPONENTS = (
    "immediate_response", "producer_native_controls", "prefix_state_reads",
    "assigned_api_continuation", "assigned_native_continuation",
    "shared_post_continuation_api_readback",
    "shared_final_native_read", "environment_reset_cleanup", "unresolved_policy",
)
FIXED_CHECKS = {
    "producer_status": "immediate_response",
    "producer_expectation": "immediate_response",
    "producer_rejection_expectation": "immediate_response",
    "native_create_form": "producer_native_controls",
    "native_POST_payload_matches_bound_intent": "producer_native_controls",
    "producer_response_matches_persisted_job": "prefix_state_reads",
    "producer_business_fields": "prefix_state_reads",
    "single_stored_resource": "prefix_state_reads",
    "rejected_prefix_left_empty_store": "prefix_state_reads",
    "rejected_prefix_full_state_unchanged": "prefix_state_reads",
    "consumer_api_loaded_bound_state": "assigned_api_continuation",
    "consumer_ui_loaded_bound_state": "assigned_native_continuation",
    "native_PUT_payload_matches_bound_intent": "assigned_native_continuation",
    "final_business_state": "shared_post_continuation_api_readback",
    "update_response_matches_persisted": "shared_post_continuation_api_readback",
    "final_single_resource": "shared_post_continuation_api_readback",
    "raw_map_preservation_observation": "shared_post_continuation_api_readback",
    "fresh_native_final_read": "shared_final_native_read",
    "initial_state_inactive_scheduler": "environment_reset_cleanup",
    "post_producer_state_inactive_scheduler": "environment_reset_cleanup",
    "final_state_inactive_scheduler": "environment_reset_cleanup",
    "no_unregistered_browser_request": "environment_reset_cleanup",
}
ASSIGNED_CHECKS = {
    "continuation_status", "continuation_submitted",
}
POLICY_CHECKS = {
    "producer_expectation", "native_PUT_payload_matches_bound_intent",
    "continuation_submitted", "raw_map_preservation_observation",
}
FINISHED_STATUSES = {
    "pass", "source_expectation_mismatch", "policy_unresolved",
    "rejection_observed_server_error",
}


def js_canonical_bytes(value):
    """Pinned adapter JSON equivalence for this finite registry's value domain.

    JS object sorting uses UTF-16 code units. Safe integers, strings, null and
    booleans serialize identically here; array order is preserved. Floats and
    unsafe integers fail closed rather than guessing ECMAScript number text.
    """
    if value is None or type(value) is bool or isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if type(value) is int and abs(value) <= 2**53 - 1:
        return str(value).encode("ascii")
    if isinstance(value, list):
        return b"[" + b",".join(js_canonical_bytes(x) for x in value) + b"]"
    if isinstance(value, dict) and all(isinstance(x, str) for x in value):
        def index_key(key):
            return key.isascii() and key.isdecimal() and str(int(key)) == key and int(key) < 2**32 - 1
        # JSON.stringify enumerates array-index property names numerically even
        # after Object.fromEntries inserts canonical keys in lexical order.
        indexes = sorted((key for key in value if index_key(key)), key=int)
        keys = indexes + sorted((key for key in value if not index_key(key)), key=lambda x: x.encode("utf-16-be"))
        return b"{" + b",".join(js_canonical_bytes(key) + b":" + js_canonical_bytes(value[key]) for key in keys) + b"}"
    raise ValueError("unsupported_json_value_for_js_hash:" + type(value).__name__)


def state_hash(value):
    return hashlib.sha256(js_canonical_bytes(value)).hexdigest()


def response_success(response):
    return (isinstance(response, dict) and response.get("kind") == "response"
            and type(response.get("status")) is int and 200 <= response["status"] < 300)


def reduce_case(result, run, registered=None, run_complete=True):
    """Reduce one result/run pair; retain observations even when unusable.

    Check IDs, per-check scope and structural route evidence drive attribution.
    result.status is used solely as an execution-completeness guard.
    """
    issues = []
    components = {name: {"checks": [], "failed_check_ids": []} for name in COMPONENTS}
    route = result.get("route")
    if route not in {"api-api", "api-ui", "ui-api", "ui-ui"}:
        issues.append("unknown_or_missing_route")
        producer_interface, consumer_interface = "unknown", "unknown"
    else:
        producer_interface, consumer_interface = route.split("-")
    assigned = "assigned_api_continuation" if consumer_interface == "api" else "assigned_native_continuation"
    accepted = result.get("accepted_prefix") is True
    unknown_policy = result.get("policy_unresolved") is True
    producer = result.get("producer", {})
    continuation = result.get("continuation", {})

    if not run_complete:
        issues.append("containing_run_incomplete_or_invalid")
    for label, data in (("result", result), ("run", run)):
        for key in ("completed", "accepted_prefix", "reached_continuation", "blocked", "timed_out"):
            if type(data.get(key)) is not bool:
                issues.append(label + "_missing_or_nonboolean_flag:" + key)
        if data.get("completed") is not True or data.get("status") not in FINISHED_STATUSES:
            issues.append(label + "_not_finished")
        if data.get("timed_out") is not False:
            issues.append(label + "_timeout_flag_not_false")
        if not data.get("ended_at"):
            issues.append(label + "_missing_end_timestamp")
    for key in ("case_id", "route", "accepted_prefix", "reached_continuation", "blocked", "initial_state_sha256"):
        if key not in result or result.get(key) != run.get(key):
            issues.append("result_run_mismatch:" + key)
    if result.get("attempted") is not True or result.get("eligible") is not True:
        issues.append("missing_attempt_or_eligibility")
    if type(result.get("policy_unresolved")) is not bool:
        issues.append("missing_or_nonboolean_policy_flag")
    if response_success(producer) != accepted:
        issues.append("producer_response_acceptance_mismatch")
    if producer.get("kind") not in {"response", "ui_block"}:
        issues.append("missing_or_unknown_producer_response_kind")
    if producer.get("kind") == "response" and type(producer.get("status")) is not int:
        issues.append("missing_producer_http_status")

    if registered is not None:
        for field, expected in (("case_id", registered["case_id"]), ("intervention", registered["intervention"]),
                                ("registered_inputs", registered["operations"]), ("expected_producer", registered["expectation"])):
            if result.get(field) != expected:
                issues.append("registry_mismatch:" + field)
        if route != "-".join(x["interface"] for x in registered["operations"]):
            issues.append("registry_mismatch:route")
        if unknown_policy != (registered["expectation"]["category"] == "unresolved"):
            issues.append("registry_mismatch:policy_unresolved")

    exit_record = run.get("child_exit", {})
    cleanup = {
        "worker_clean_exit": exit_record.get("code") == 0 and not exit_record.get("signal")
                             and not exit_record.get("exit_unconfirmed") and not exit_record.get("spawn_error"),
        "node_cleanup": run.get("node_cleanup", {}).get("ok") is True,
        "java_cleanup": run.get("java_cleanup", {}).get("ok") is True,
        "browser_cleanup": run.get("browser_cleanup", {}).get("ok") is True,
        "browser_absent": run.get("browser_process_absent") is True,
        "port_released": run.get("application_port_released") is True,
    }
    for key, passed in cleanup.items():
        if not passed:
            issues.append("execution_guard:" + key)
    for key in ("error", "cleanup_error", "interruption"):
        if result.get(key):
            issues.append("result_contains:" + key)
    for key in ("page_errors", "blocked_requests"):
        if not isinstance(result.get(key), list) or result[key]:
            issues.append("unresolved_browser_evidence:" + key)

    checks = result.get("checks", [])
    if not isinstance(checks, list):
        checks = []
        issues.append("checks_not_a_list")
    observed = {}
    unclassified = []
    for check in checks:
        if not isinstance(check, dict):
            issues.append("malformed_check")
            continue
        check_id = check.get("id")
        target = FIXED_CHECKS.get(check_id)
        if check_id in ASSIGNED_CHECKS:
            target = assigned
        if target is None:
            unclassified.append(check_id)
            issues.append("unknown_check_id:" + str(check_id))
            continue
        if check_id in observed:
            issues.append("duplicate_check_id:" + check_id)
        observed[check_id] = check
        required_scope = "unresolved_policy" if unknown_policy and check_id in POLICY_CHECKS else "requirement"
        if check.get("scope") != required_scope or type(check.get("passed")) is not bool:
            issues.append("invalid_check_scope_or_value:" + check_id)
            continue
        origin = target
        if origin == "producer_native_controls" and producer_interface != "ui":
            issues.append("native_producer_check_on_api_route:" + check_id)
            unclassified.append(check_id)
            continue
        downstream = origin.startswith("assigned_") or origin in {"shared_post_continuation_api_readback", "shared_final_native_read"}
        if (downstream and not accepted) or (origin.startswith("assigned_") and origin != assigned):
            issues.append("check_in_wrong_route_or_rejected_prefix:" + check_id)
            unclassified.append(check_id)
            continue
        if check["scope"] == "unresolved_policy":
            target = "unresolved_policy"
        item = {"id": check_id, "passed": check["passed"], "scope": check["scope"], "origin_component": origin}
        components[target]["checks"].append(item)
        if not check["passed"]:
            components[target]["failed_check_ids"].append(check_id)
            if target == "environment_reset_cleanup":
                issues.append("execution_condition_check_failed:" + check_id)

    required = {"initial_state_inactive_scheduler", "post_producer_state_inactive_scheduler", "no_unregistered_browser_request"}
    if producer_interface == "ui":
        required.add("native_create_form")
        if producer.get("kind") == "response":
            required.add("native_POST_payload_matches_bound_intent")
    if accepted:
        required |= {"producer_status", "producer_response_matches_persisted_job", "producer_business_fields",
                     "single_stored_resource", "final_business_state", "fresh_native_final_read",
                     "final_state_inactive_scheduler", "final_single_resource"}
        required.add("consumer_api_loaded_bound_state" if consumer_interface == "api" else "consumer_ui_loaded_bound_state")
        if result.get("reached_continuation") is not True:
            issues.append("accepted_prefix_without_reached_continuation")
        if result.get("expected_producer", {}).get("outcome") == "reject":
            required.add("producer_rejection_expectation")
        if continuation.get("kind") == "response":
            required.add("continuation_status")
            if type(continuation.get("status")) is not int:
                issues.append("missing_continuation_http_status")
            if consumer_interface == "ui":
                required.add("native_PUT_payload_matches_bound_intent")
            if response_success(continuation):
                required.add("update_response_matches_persisted")
        elif continuation.get("kind") in {"ui_block", "representation_block"} and consumer_interface == "ui":
            required.add("continuation_submitted")
            if result.get("blocked") is not True:
                issues.append("native_block_without_blocked_flag")
        else:
            issues.append("missing_or_unknown_continuation_kind")
        if unknown_policy:
            required.add("raw_map_preservation_observation")
        for key in ("bindings", "stored_prefix", "final_job"):
            if not isinstance(result.get(key), dict):
                issues.append("missing_accepted_prefix_evidence:" + key)
        if result.get("bindings", {}).get("path") != JOB_PATH:
            issues.append("missing_or_unregistered_bound_path")
    else:
        required |= {"rejected_prefix_left_empty_store", "rejected_prefix_full_state_unchanged", "producer_expectation"}
        if result.get("reached_continuation") is not False or continuation.get("attempted") is not False:
            issues.append("rejected_prefix_has_continuation_or_missing_stop_record")
        if result.get("consumption_observations") != []:
            issues.append("rejected_prefix_has_consumption_or_missing_empty_record")
    for check_id in sorted(required - observed.keys()):
        issues.append("missing_required_check:" + check_id)
    for check_id in sorted(observed.keys() - required):
        issues.append("unexpected_check_for_execution_branch:" + check_id)

    recomputed_hashes = {}
    for state in ("initial_state", "post_producer_state", "final_state"):
        value = result.get(state)
        if not isinstance(value, dict) or any(key not in value for key in ("scheduler", "jobs", "triggers")):
            issues.append("missing_state_evidence:" + state)
            continue
        try:
            actual_hash = state_hash(value)
        except (ValueError, UnicodeError) as error:
            issues.append("unverifiable_state_hash:" + state + ":" + str(error))
            continue
        recomputed_hashes[state] = actual_hash
        recorded = result.get(state + "_sha256")
        if recorded is None and (state != "final_state" or accepted):
            issues.append("missing_required_state_hash:" + state)
        elif recorded is not None and recorded != actual_hash:
            issues.append("recorded_state_hash_mismatch:" + state)
        if state in {"initial_state", "final_state"} and run.get(state + "_sha256") != actual_hash:
            issues.append("run_state_hash_mismatch:" + state)
    actor = result.get("api_actor")
    if (not isinstance(actor, dict) or actor.get("username") != "admin"
            or {"authority": "ROLE_ADMIN"} not in actor.get("authorities", [])):
        issues.append("missing_or_incorrect_api_actor")
    actors = result.get("actors", [])
    if not isinstance(actors, list) or any(x.get("principal") != actor for x in actors):
        issues.append("actor_observation_mismatch")
        actors = []
    forms = result.get("ui_forms", [])
    if not isinstance(forms, list):
        forms = []
        issues.append("missing_native_form_evidence")
    form_labels = {x.get("label") for x in forms if isinstance(x, dict)}
    expected_forms = {"producer_form"} if producer_interface == "ui" else set()
    if accepted:
        expected_forms.add("fresh_final_native_read")
        if consumer_interface == "ui":
            expected_forms.add("consumer_loaded")
            if continuation.get("kind") != "representation_block":
                expected_forms.add("consumer_before_submit")
        expected_ui_phases = {"final_read"} | ({"producer"} if producer_interface == "ui" else set()) | ({"continuation"} if consumer_interface == "ui" else set())
    else:
        expected_ui_phases = {"producer"} if producer_interface == "ui" else set()
    for phase in sorted(expected_ui_phases):
        if not any(x.get("interface") == "ui" and x.get("phase") == phase for x in actors):
            issues.append("missing_native_actor_observation:" + phase)
    for label in sorted(expected_forms - form_labels):
        issues.append("missing_native_form:" + label)

    trace = result.get("trace", [])
    if not isinstance(trace, list):
        trace = []
        issues.append("trace_not_a_list")

    def require_request(source, method, path, minimum=1):
        # Browser response handlers are asynchronous: trace.phase may have
        # advanced. It never assigns or reassigns a component in this reducer.
        count = sum(isinstance(x, dict) and (x.get("source"), x.get("method"), x.get("path")) == (source, method, path) for x in trace)
        if count < minimum:
            issues.append("missing_request:" + ":".join((source, method, path)) + ":minimum=" + str(minimum))

    require_request("direct_api", "POST", "/quartz-manager/auth/login")
    require_request("direct_api", "GET", "/quartz-manager/auth/whoami")
    if producer.get("kind") == "response":
        require_request("direct_api" if producer_interface == "api" else "ui_network", "POST", JOB_PATH)
    if accepted:
        require_request("direct_api", "GET", JOB_PATH, 3 if consumer_interface == "api" else 2)
        if continuation.get("kind") == "response":
            require_request("direct_api" if consumer_interface == "api" else "ui_network", "PUT", JOB_PATH)

    issues = sorted(set(issues))
    for name, component in components.items():
        component["mismatch_observed"] = bool(component["failed_check_ids"])
        applicable = bool(component["checks"]) or name == "environment_reset_cleanup"
        if name.startswith("assigned_"):
            applicable = accepted and name == assigned
        if name in {"shared_post_continuation_api_readback", "shared_final_native_read"}:
            applicable = accepted
        if name == "unresolved_policy":
            component["status"] = "policy_observations_only" if component["checks"] else "not_applicable"
            component["comparison_eligible"] = False
        elif not applicable:
            component["status"] = "not_reached_prefix_rejected" if not accepted and (name.startswith("assigned_") or name in {"shared_post_continuation_api_readback", "shared_final_native_read"}) else "not_applicable"
            component["comparison_eligible"] = False
        else:
            component["comparison_eligible"] = not issues
            component["status"] = "incomplete_or_invalid_evidence" if issues else "check_mismatch_observed" if component["mismatch_observed"] else "no_check_mismatch_observed"
    components["environment_reset_cleanup"]["execution_guards"] = cleanup
    components["shared_post_continuation_api_readback"]["assigned_action_interface"] = consumer_interface if accepted else None
    components["shared_post_continuation_api_readback"]["observation_mechanism"] = "Direct API reads after the assigned action; not native-only detection."
    return {
        "case_id": result.get("case_id"), "route": route,
        "execution_evidence_complete": not issues, "evidence_issues": issues,
        "accepted_prefix": accepted, "assigned_continuation_reached": result.get("reached_continuation") is True,
        "producer_response": {"kind": producer.get("kind"), "status": producer.get("status")},
        "continuation_response": {"kind": continuation.get("kind"), "status": continuation.get("status")},
        "policy_unresolved": unknown_policy, "components": components,
        "recomputed_state_sha256": recomputed_hashes,
        "unclassified_check_ids": unclassified,
        "interpretation": "Recorded source-check observations only; no defect, root-cause or detection-overlap classification.",
    }


def summarize_run(directory):
    directory = Path(directory).resolve()
    summary_bytes = (directory / "summary.json").read_bytes()
    summary = json.loads(summary_bytes)
    issues = []
    for filename, expected in (("executed-adapter.mjs", ADAPTER_SHA256), ("executed-registry.json", REGISTRY_SHA256)):
        path = directory / filename
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            issues.append("unsupported_or_missing_pinned_artifact:" + filename)
    if summary.get("adapter_sha256") != ADAPTER_SHA256 or summary.get("registry_sha256") != REGISTRY_SHA256:
        issues.append("summary_pins_do_not_match_supported_evidence")
    registry = json.loads((directory / "executed-registry.json").read_text())
    mode = summary.get("mode")
    if mode not in {"controls", "all"}:
        issues.append("unknown_run_mode")
    wanted = {c["case_id"]: c for c in registry["cases"] if mode == "all" or c["intervention"] == "route_only"}
    entries = summary.get("cases", [])
    ids = [entry.get("case_id") for entry in entries]
    if len(ids) != len(set(ids)) or set(ids) != set(wanted) or summary.get("case_count") != len(wanted):
        issues.append("missing_duplicate_or_unregistered_cases")
    if summary.get("status") not in {"pass", "completed_observations"} or not summary.get("ended_at"):
        issues.append("run_not_finished")
    if summary.get("equal_initial_state_hashes") is not True:
        issues.append("run_initial_states_not_confirmed_equal")
    initial_hashes = [entry.get("initial_state_sha256") for entry in entries]
    if not initial_hashes or not all(initial_hashes) or len(set(initial_hashes)) != 1:
        issues.append("run_initial_hash_records_missing_or_different")
    loaded = []
    used_directories = set()
    for entry in entries:
        # CI artifact extraction relocates absolute evidence paths. Resolve only
        # the unique immediate child directory name, never the recorded host path.
        leaf = Path(entry.get("evidence_directory", "")).name
        if not leaf or leaf in {".", ".."} or leaf in used_directories:
            issues.append("invalid_or_duplicate_evidence_directory")
            continue
        used_directories.add(leaf)
        case_dir = directory / leaf
        if case_dir.resolve().parent != directory:
            issues.append("evidence_directory_escapes_run")
            continue
        try:
            result_bytes = (case_dir / "result.json").read_bytes()
            run_bytes = (case_dir / "run.json").read_bytes()
            result = json.loads(result_bytes)
            run = json.loads(run_bytes)
        except (OSError, ValueError) as error:
            issues.append("unreadable_case_evidence:" + leaf + ":" + type(error).__name__)
            continue
        if run != entry:
            issues.append("summary_case_differs_from_run_record:" + leaf)
        input_hashes = {"result.json": hashlib.sha256(result_bytes).hexdigest(), "run.json": hashlib.sha256(run_bytes).hexdigest()}
        loaded.append((leaf, result, run, wanted.get(entry.get("case_id")), input_hashes))
    observations = []
    for leaf, result, run, registered, input_hashes in loaded:
        observation = reduce_case(result, run, registered, run_complete=not issues)
        observation["evidence_directory"] = leaf
        observation["input_sha256"] = input_hashes
        observations.append(observation)
    complete = not issues and len(observations) == len(wanted) and all(x["execution_evidence_complete"] for x in observations)
    return {
        "schema_version": 1, "kind": "quartz_component_observations",
        "status": "complete_observations" if complete else "incomplete_or_invalid_evidence",
        "input_directory": str(directory), "input_summary_sha256": hashlib.sha256(summary_bytes).hexdigest(),
        "reducer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "supported_adapter_sha256": ADAPTER_SHA256, "supported_registry_sha256": REGISTRY_SHA256,
        "run_issues": sorted(set(issues)), "case_count": len(observations), "cases": observations,
        "component_status_counts": {name: dict(Counter(x["components"][name]["status"] for x in observations)) for name in COMPONENTS},
        "limitations": [
            "Attribution of existing recorded checks, not an independent re-execution or validation of the application oracle.",
            "Supplementary final native reads are isolated from assigned API/native continuation checks.",
            "Post-continuation API readback is shared verification with action-route metadata, not native-only observation on UI routes.",
            "Incomplete evidence retains observations but supplies no clean comparative outcome; rejected prefixes supply no downstream signal.",
            "A later shared-read failure may leave earlier channel checks present while the overall case remains incomplete; those earlier observations are not a complete pair classification.",
            "Per-check unresolved-policy scope is separate; unrelated requirement-check mismatches remain visible.",
            "State-hash verification uses the pinned JS canonical form for strings, booleans, null and safe integer JSON; unsupported numeric forms fail closed.",
            "No paired-prefix equivalence, repeat schedule, human adjudication, defect labels, root-cause grouping or detection-overlap computation is implemented.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    args = parser.parse_args()
    try:
        output = summarize_run(args.run_directory)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        output = {"kind": "quartz_component_observations", "status": "incomplete_or_invalid_evidence",
                  "run_issues": ["unreadable_or_malformed_run:" + type(error).__name__ + ":" + str(error)], "cases": []}
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0 if output["status"] == "complete_observations" else 1


if __name__ == "__main__":
    raise SystemExit(main())
