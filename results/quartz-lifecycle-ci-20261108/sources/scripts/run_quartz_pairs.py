#!/usr/bin/env python3
"""Run only the four registered Quartz controls as two independent prefix pairs.

Writes a hashed plan and copies its inputs before dispatch. No boundary mode,
resume, automatic retries, detection-overlap or defect classification exists.
The paired-control protocol fixes 75s/case, 330s/campaign, 110s shutdown grace
and 5s kill confirmation. An unsuccessful attempt must be retained in full.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

import summarize_quartz_oracle_components as components


PROJECT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    "scripts/run_quartz_pairs.py", "scripts/run_quartz_registry.mjs",
    "scripts/quartz_generated_case.mjs", "scripts/summarize_quartz_oracle_components.py",
    "scripts/quartz_browser_cleanup.py", "scripts/realworld_case_worker.py",
    "protocol/paired-control-validation-v1.md", "manifests/quartz-artifact-lock.json",
)
TIMEOUTS = {"case_timeout_ms": 75000, "campaign_timeout_s": 330,
            "shutdown_grace_s": 110, "kill_confirmation_s": 5}
BUSINESS_FIELDS = ("jobKeyDTO", "jobClassName", "description", "durable", "requestsRecovery", "jobDataMap", "triggerKeys")
ARCHIVED_RUN_SOURCES = {
    "scripts/run_quartz_registry.mjs": "executed-runner.mjs",
    "scripts/quartz_generated_case.mjs": "executed-adapter.mjs",
    "scripts/quartz_browser_cleanup.py": "executed-quartz_browser_cleanup.py",
    "scripts/realworld_case_worker.py": "executed-realworld_case_worker.py",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def runner_command(effective, project):
    command = [effective["node"], str(Path(project) / "scripts/run_quartz_registry.mjs")]
    for option, key in (("runtime", "runtime"), ("java", "java"), ("node", "node"), ("python", "python"),
                        ("registry", "registry"), ("output", "output"), ("mode", "mode"), ("port", "port"),
                        ("case-timeout-ms", "case_timeout_ms"), ("case-order-file", "case_order_file"),
                        ("playwright-module", "playwright_module"), ("chrome-executable", "chrome_executable")):
        command.extend(["--" + option, str(effective[key])])
    return command


def build_pairs(registry):
    """Pure construction from the pinned catalog, with exact control allowlist."""
    controls = [case for case in registry["cases"] if case["intervention"] == "route_only"]
    if len(registry["cases"]) != 44 or len(controls) != 4:
        raise ValueError("Expected unchanged 44-case registry with four ordinary controls")
    by_route = {}
    for case in controls:
        route = "-".join(operation["interface"] for operation in case["operations"])
        if route in by_route or route not in {"api-api", "api-ui", "ui-api", "ui-ui"} or case.get("mutation"):
            raise ValueError("Duplicate, unknown or mutated control route")
        if case["expectation"]["outcome"] != "accept" or case["expectation"]["category"] != "implementation_control":
            raise ValueError("Control expectation changed")
        by_route[route] = case
    pairs = []
    for producer, consumers in (("api", ("api", "ui")), ("ui", ("ui", "api"))):
        cases = [by_route[producer + "-" + consumer] for consumer in consumers]
        if cases[0]["operations"][0] != cases[1]["operations"][0]:
            raise ValueError("Control pair does not have the same producer operation")
        consumer_intents = [{k: v for k, v in case["operations"][1].items() if k != "interface"} for case in cases]
        if consumer_intents[0] != consumer_intents[1]:
            raise ValueError("Control pair consumer intent differs")
        for key in ("expectation", "expectation_scope"):
            if cases[0].get(key) != cases[1].get(key):
                raise ValueError("Control pair expectation or scope differs")
        pair = {"pair_id": "quartz-control-prefix-" + producer, "producer_interface": producer,
                "consumer_order": list(consumers), "case_ids": [case["case_id"] for case in cases],
                "producer_operation": cases[0]["operations"][0], "consumer_intent": consumer_intents[0],
                "expectation": cases[0]["expectation"], "expectation_scope": cases[0]["expectation_scope"],
                "hash_encoding": "sorted-key indent-2 UTF-8 JSON with final newline; registry numbers preserved by Python JSON",
                "case_sha256": {case["case_id"]: sha(json_bytes(case)) for case in cases}}
        pair["pair_sha256"] = sha(json_bytes(pair))
        pairs.append(pair)
    return pairs


def prepare_plan(config, output, project=PROJECT):
    output, project = Path(output).resolve(), Path(project).resolve()
    registry_bytes = Path(config["registry"]).read_bytes()
    if sha(registry_bytes) != components.REGISTRY_SHA256:
        raise ValueError("Registry bytes differ from the pinned v2 pool")
    registry = json.loads(registry_bytes)
    pairs = build_pairs(registry)
    sources = {name: (project / name).read_bytes() for name in SOURCE_FILES}
    if sha(sources["scripts/quartz_generated_case.mjs"]) != components.ADAPTER_SHA256:
        raise ValueError("The component mapping does not support this adapter")
    sidecars = {"environment.json": Path(config["environment_file"]).read_bytes(),
                "browser.json": Path(config["browser_info"]).read_bytes()}
    if not all(isinstance(json.loads(data), dict) and json.loads(data) for data in sidecars.values()):
        raise ValueError("Nonempty environment/browser JSON objects are required")
    environment, browser = json.loads(sidecars["environment.json"]), json.loads(sidecars["browser.json"])
    if not isinstance(environment.get("node", {}).get("output"), str) or environment["node"].get("exit_code") != 0:
        raise ValueError("Environment must contain a successful captured Node version")
    browser_version = browser.get("declared", {}).get("browserVersion")
    if (not isinstance(browser_version, str) or browser_version not in re.findall(r"\d+\.\d+\.\d+\.\d+", str(browser.get("actual_version", "")))
            or not isinstance(browser.get("executable"), str) or Path(browser["executable"]).resolve() != Path(config["chrome_executable"]).resolve()):
        raise ValueError("Captured browser version/path does not identify the planned browser")
    output.mkdir(parents=True, exist_ok=False)
    for name, data in sources.items():
        write_new(output / "sources" / name, data)
    for name, data in {"registry.json": registry_bytes, **sidecars}.items():
        write_new(output / "inputs" / name, data)
    order = {"schema_version": 1, "scope": "quartz_route_controls", "registry_sha256": components.REGISTRY_SHA256,
             "case_ids": [case_id for pair in pairs for case_id in pair["case_ids"]]}
    order_bytes = json_bytes(order)
    write_new(output / "case-order.json", order_bytes)
    effective = {key: str(config[key]) for key in ("runtime", "java", "node", "python", "playwright_module", "chrome_executable")}
    effective.update(mode="controls", registry=str(output / "inputs/registry.json"), output=str(output / "run"),
                     port=config.get("port", 19965), case_timeout_ms=TIMEOUTS["case_timeout_ms"],
                     case_order_file=str(output / "case-order.json"), validation_interrupt_at=None)
    command = runner_command(effective, project)
    lock = json.loads(sources["manifests/quartz-artifact-lock.json"])
    artifacts = [x for x in lock["artifacts"] if x["name"].endswith(".jar")] + lock["additional_declared_dependencies"]
    plan = {"schema_version": 1, "kind": "quartz_paired_control_plan", "scope": "ordinary_controls_only",
            "created_at_utc": datetime.now(timezone.utc).isoformat(), "prepared_before_dispatch": True,
            "source_project": str(project), "sources": {name: sha(data) for name, data in sources.items()},
            "inputs": {"inputs/registry.json": sha(registry_bytes), **{"inputs/" + k: sha(v) for k, v in sidecars.items()}, "case-order.json": sha(order_bytes)},
            "registry_manifest_sha256": registry["manifest_sha256"], "pairs": pairs, "case_ids": order["case_ids"],
            "effective_options": effective, "command": command, "timeouts": dict(TIMEOUTS),
            "expected_runtime_artifacts": {x["name"]: x["sha256"] for x in artifacts},
            "partial_repeat_policy": "No resume, replacement, automatic repeat or cross-attempt merging. Preserve an invalid attempt; any correction requires a fresh complete four-control attempt.",
            "comparison": "Exact recorded producer inputs, actors, full initial state, declared post-prefix business fields and intended bound consumer commands. JSON object order only is immaterial. Fresh independent branches, no sequential dual edits.",
            "limits": ["Two exposed ordinary control pairs, one workflow, one application.", "No boundary, primary freeze, defect, root-cause, detection-overlap, selector or timing-effectiveness inference.", "Actual deadline-path validation remains separate; shutdown is bounded but not claimed prompt."]}
    plan_bytes = json_bytes(plan)
    write_new(output / "plan.json", plan_bytes)
    write_new(output / "plan.sha256", (sha(plan_bytes) + "\n").encode())
    return plan


def verify_plan(output, live_sources=False):
    output = Path(output).resolve()
    data = (output / "plan.json").read_bytes()
    if sha(data) != (output / "plan.sha256").read_text().strip():
        raise ValueError("Frozen plan hash differs")
    plan = json.loads(data)
    if set(plan["sources"]) != set(SOURCE_FILES) or set(plan["inputs"]) != {"inputs/registry.json", "inputs/environment.json", "inputs/browser.json", "case-order.json"}:
        raise ValueError("Frozen artifact inventory is incomplete or changed")
    if plan.get("scope") != "ordinary_controls_only" or plan.get("timeouts") != TIMEOUTS:
        raise ValueError("Control scope or timeout policy changed")
    if (plan["effective_options"]["mode"] != "controls" or plan["effective_options"]["case_timeout_ms"] != TIMEOUTS["case_timeout_ms"]
            or plan["command"] != runner_command(plan["effective_options"], plan["source_project"])):
        raise ValueError("Effective control command differs from the frozen policy")
    for name, expected in plan["sources"].items():
        if sha((output / "sources" / name).read_bytes()) != expected:
            raise ValueError("Archived source differs: " + name)
        if live_sources and sha((Path(plan["source_project"]) / name).read_bytes()) != expected:
            raise ValueError("Live source differs: " + name)
    for name, expected in plan["inputs"].items():
        if sha((output / name).read_bytes()) != expected:
            raise ValueError("Frozen input differs: " + name)
    if plan["inputs"]["inputs/registry.json"] != components.REGISTRY_SHA256:
        raise ValueError("Unsupported registry provenance")
    registry = json.loads((output / "inputs/registry.json").read_bytes())
    pairs = build_pairs(registry)
    if pairs != plan["pairs"] or plan["case_ids"] != [cid for pair in pairs for cid in pair["case_ids"]]:
        raise ValueError("Pair membership, case hashes or order changed")
    order = json.loads((output / "case-order.json").read_bytes())
    if order != {"schema_version": 1, "scope": "quartz_route_controls", "registry_sha256": components.REGISTRY_SHA256, "case_ids": plan["case_ids"]}:
        raise ValueError("Case order differs from frozen pair order")
    return plan


@contextmanager
def bounded_shutdown_signals():
    """Finish the already bounded teardown despite repeated stop signals."""
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        for sig in previous:
            signal.signal(sig, signal.SIG_IGN)
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def run_bounded(command, cwd, log_path, timeout=330, grace=110, kill_wait=5):
    """Signal only the direct runner; it owns JVM/browser cleanup.

    Hard killing the runner does not prove descendant cleanup and always leaves
    the attempt invalid. Never launch a replacement runner in this function.
    """
    start = time.monotonic()
    record = {"started_at_utc": datetime.now(timezone.utc).isoformat(), "timed_out": False,
              "interrupted": False, "hard_kill": False, "exit_confirmed": False}
    process = None
    with Path(log_path).open("xb") as log:
        try:
            process = subprocess.Popen(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
            record["pid"] = process.pid
            record["returncode"] = process.wait(timeout=timeout)
            record["exit_confirmed"] = True
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
            record["timed_out"] = isinstance(error, subprocess.TimeoutExpired)
            record["interrupted"] = isinstance(error, KeyboardInterrupt)
            if process is not None:
                # An owned child can exit between timeout detection and a
                # signal. Record that race and still confirm exit with wait().
                def signal_owned(method, label):
                    try:
                        method()
                        record[label] = "sent"
                    except ProcessLookupError:
                        record[label] = "already_exited_before_signal"
                        record[label + "_poll"] = process.poll()
                    except OSError as signal_error:
                        record[label] = "signal_error:" + str(signal_error)

                with bounded_shutdown_signals():
                    signal_owned(process.terminate, "terminate_disposition")
                    try:
                        record["returncode"] = process.wait(timeout=grace)
                        record["exit_confirmed"] = True
                    except subprocess.TimeoutExpired:
                        record["hard_kill"] = True
                        signal_owned(process.kill, "kill_disposition")
                        try:
                            record["returncode"] = process.wait(timeout=kill_wait)
                            record["exit_confirmed"] = True
                        except subprocess.TimeoutExpired:
                            record["returncode"] = None
        except OSError as error:
            record["spawn_error"] = str(error)
    record["elapsed_s"] = time.monotonic() - start
    record["ended_at_utc"] = datetime.now(timezone.utc).isoformat()
    record["successful_exit"] = record.get("returncode") == 0 and record["exit_confirmed"] and not any(record[k] for k in ("timed_out", "interrupted", "hard_kill"))
    record["cleanup_confirmation"] = "requires_case_evidence" if not record["hard_kill"] else "unconfirmed_after_runner_hard_kill"
    return record


def business(job):
    if not isinstance(job, dict) or any(key not in job for key in BUSINESS_FIELDS):
        raise ValueError("Missing declared post-prefix business fields")
    return {key: job[key] for key in BUSINESS_FIELDS}


def pair_observations(plan_pair, records, extracted, campaign_issues=()):
    issues = list(campaign_issues)
    comparisons = {}
    branches = []
    for cid in plan_pair["case_ids"]:
        item = records.get(cid)
        observation = extracted.get(cid)
        if item is None or observation is None:
            issues.append("missing_branch:" + cid)
            continue
        result, run, directory = item
        branches.append({"case_id": cid, "evidence_directory": str(directory), "components": observation["components"],
                         "input_sha256": observation.get("input_sha256"), "recorded_elapsed_ms": run.get("elapsed_ms"),
                         "recorded_phase_cost_ms": run.get("phase_cost_ms")})
        if not observation["execution_evidence_complete"]:
            issues.append("incomplete_component_evidence:" + cid)
        if result.get("accepted_prefix") is not True or not components.response_success(result.get("producer")):
            issues.append("prefix_not_accepted:" + cid)
    if len(branches) == 2:
        try:
            first, second = [records[cid] for cid in plan_pair["case_ids"]]
            results = [first[0], second[0]]
            comparisons["independent_evidence_directories"] = first[2].resolve() != second[2].resolve()
            pids = [first[1].get("server_pid"), second[1].get("server_pid")]
            comparisons["independent_jvm_pid_evidence"] = all(type(pid) is int and pid > 0 for pid in pids) and pids[0] != pids[1]
            comparisons["same_actor"] = results[0]["api_actor"] == results[1]["api_actor"]
            comparisons["same_full_initial_state"] = results[0]["initial_state"] == results[1]["initial_state"]
            comparisons["same_initial_state_hash"] = results[0]["initial_state_sha256"] == results[1]["initial_state_sha256"]
            comparisons["same_registered_prefix"] = all(r["registered_inputs"][0] == plan_pair["producer_operation"] for r in results)
            comparisons["actual_producer_input_matches_registered"] = all(r["producer"]["request"] == plan_pair["producer_operation"]["input"] for r in results)
            states = [business(r["stored_prefix"]) for r in results]
            comparisons["same_accepted_postprefix_business_state"] = states[0] == states[1]
            comparisons["producer_response_matches_stored_prefix"] = all(business(r["producer"]["body"]) == state for r, state in zip(results, states))
            comparisons["postprefix_collection_matches_stored_resource"] = all(len(r["post_producer_state"]["jobs"]) == 1 and business(r["post_producer_state"]["jobs"][0]) == state for r, state in zip(results, states))
            intended = []
            for result, state in zip(results, states):
                intended.append({"jobClass": state["jobClassName"], "description": plan_pair["consumer_intent"]["input"]["description"],
                                 "durable": state["durable"], "requestsRecovery": state["requestsRecovery"], "jobDataMap": state["jobDataMap"]})
            comparisons["same_intended_bound_consumer_payload"] = intended[0] == intended[1]
            comparisons["consumer_binding_matches_prefix_state"] = all(r["bindings"]["command"] == command and r["bindings"]["path"] == components.JOB_PATH for r, command in zip(results, intended))
            comparisons["actual_consumer_payload_matches_bound_intent"] = all(r["continuation"].get("kind") == "response" and r["continuation"].get("request") == command for r, command in zip(results, intended))
            comparisons["same_registered_consumer_intent"] = all({k: v for k, v in r["registered_inputs"][1].items() if k != "interface"} == plan_pair["consumer_intent"] for r in results)
            comparisons["consumer_order_matches_plan"] = [r["route"].split("-")[1] for r in results] == plan_pair["consumer_order"]
            comparisons["ordinary_response_statuses"] = all(r["producer"].get("status") == 201 and r["continuation"].get("status") == 200 for r in results)
            comparisons["clean_ordinary_controls"] = all(not component["failed_check_ids"] for branch in branches for component in branch["components"].values())
        except (KeyError, TypeError, ValueError, IndexError) as error:
            issues.append("missing_or_invalid_pair_evidence:" + str(error))
        issues += ["pair_comparison_failed:" + key for key, passed in comparisons.items() if not passed]
    else:
        issues.append("pair_not_complete")
    return {"pair_id": plan_pair["pair_id"], "pair_sha256": plan_pair["pair_sha256"], "valid": not issues,
            "status": "valid_control_pair" if not issues else "invalid_control_pair", "issues": sorted(set(issues)),
            "comparisons": comparisons, "branches": branches,
            "interpretation": "Engineering control-pair validity and component observations only; no detection-overlap or defect label."}


def summarize_campaign(output, execution):
    output = Path(output).resolve()
    plan = verify_plan(output)
    issues = []
    if execution.get("successful_exit") is not True:
        issues.append("runner_did_not_finish_successfully")
    run_dir = output / "run"
    summary = json.loads((run_dir / "summary.json").read_bytes())
    if summary.get("effective_options") != plan["effective_options"]:
        issues.append("runner_effective_options_differ_from_plan")
    if summary.get("ordering") != {"source": "case_order_file", "case_ids": plan["case_ids"], "order_file_sha256": plan["inputs"]["case-order.json"]}:
        issues.append("runner_ordering_differs_from_plan")
    if [x.get("case_id") for x in summary.get("cases", [])] != plan["case_ids"]:
        issues.append("actual_execution_order_or_completeness_differs")
    if summary.get("runner_sha256") != plan["sources"]["scripts/run_quartz_registry.mjs"]:
        issues.append("runner_source_hash_differs")
    for source, archived in ARCHIVED_RUN_SOURCES.items():
        if sha((run_dir / archived).read_bytes()) != plan["sources"][source]:
            issues.append("executed_source_differs:" + source)
    if sha((run_dir / "executed-case-order.json").read_bytes()) != plan["inputs"]["case-order.json"]:
        issues.append("executed_order_file_differs")
    runtime = Path(plan["effective_options"]["runtime"])
    artifacts = {str(Path(x["file"]).relative_to(runtime)): x["sha256"] for x in summary["runtime"]["artifacts"]}
    if artifacts != plan["expected_runtime_artifacts"]:
        issues.append("runtime_artifact_inventory_differs")
    environment = json.loads((output / "inputs/environment.json").read_bytes())
    browser = json.loads((output / "inputs/browser.json").read_bytes())
    environment_checks = {
        "node_version_matches_capture": summary.get("node_version") == environment["node"]["output"].strip(),
        "browser_path_matches_plan": Path(browser["executable"]).resolve() == Path(plan["effective_options"]["chrome_executable"]).resolve(),
        "browser_declared_version_matches_capture": browser["declared"]["browserVersion"] in re.findall(r"\d+\.\d+\.\d+\.\d+", browser["actual_version"]),
    }
    # Load the exact archived reducer whose hash was frozen before dispatch.
    reducer_path = output / "sources/scripts/summarize_quartz_oracle_components.py"
    spec = importlib.util.spec_from_file_location("frozen_quartz_components", reducer_path)
    reducer = importlib.util.module_from_spec(spec)
    old_bytecode = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(reducer)
    finally:
        sys.dont_write_bytecode = old_bytecode
    reduced = reducer.summarize_run(run_dir)
    if reduced["reducer_sha256"] != plan["sources"]["scripts/summarize_quartz_oracle_components.py"]:
        issues.append("component_reducer_source_differs")
    if reduced["status"] != "complete_observations":
        issues.append("component_evidence_incomplete_or_invalid")
    write_new(output / "components.json", json_bytes(reduced))
    records = {}
    for entry in summary.get("cases", []):
        directory = run_dir / Path(entry["evidence_directory"]).name
        if directory.resolve().parent != run_dir.resolve():
            issues.append("case_evidence_escapes_run")
            continue
        records[entry["case_id"]] = (json.loads((directory / "result.json").read_bytes()), json.loads((directory / "run.json").read_bytes()), directory)
    environment_checks["case_browser_versions_match_capture"] = bool(records) and all(record[0].get("browser_version") == browser["declared"]["browserVersion"] for record in records.values())
    issues += ["environment_capture_mismatch:" + key for key, passed in environment_checks.items() if not passed]
    observations = {x["case_id"]: x for x in reduced["cases"]}
    pairs = [pair_observations(pair, records, observations, issues) for pair in plan["pairs"]]
    return {"schema_version": 1, "kind": "quartz_paired_control_observations", "scope": "ordinary_controls_only",
            "status": "valid_control_pairs" if all(x["valid"] for x in pairs) else "invalid_attempt",
            "plan_sha256": sha((output / "plan.json").read_bytes()), "execution": execution,
            "campaign_issues": issues, "environment_checks": environment_checks, "pairs": pairs, "pair_count": 2, "case_count": len(records),
            "partial_repeat_policy": plan["partial_repeat_policy"], "primary_freeze_complete": False,
            "limits": plan["limits"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("runtime", "java", "node", "registry", "output", "playwright-module", "chrome-executable", "environment-file", "browser-info"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--port", type=int, default=19965)
    parser.add_argument("--prepare-only", action="store_true", help="Save/validate a new plan without launching any application; it cannot later be resumed.")
    args = parser.parse_args()
    config = vars(args)
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    for key in ("runtime", "registry", "output", "environment_file", "browser_info"):
        config[key] = str(Path(config[key]).resolve())
    output = Path(config["output"])
    plan = prepare_plan(config, output)
    verify_plan(output, live_sources=True)
    if args.prepare_only:
        print(json.dumps({"status": "plan_prepared_no_execution", "output": str(output)}))
        return 0
    dispatch = {"started_at_utc": datetime.now(timezone.utc).isoformat(), "plan_sha256": sha((output / "plan.json").read_bytes())}
    write_new(output / "dispatch.json", json_bytes(dispatch))
    previous = signal.getsignal(signal.SIGTERM)
    def interrupt_campaign(*_):
        raise KeyboardInterrupt("Campaign stop requested")
    signal.signal(signal.SIGTERM, interrupt_campaign)
    try:
        execution = run_bounded(plan["command"], plan["source_project"], output / "runner.log")
    finally:
        signal.signal(signal.SIGTERM, previous)
    write_new(output / "execution.json", json_bytes(execution))
    try:
        verify_plan(output, live_sources=True)
        result = summarize_campaign(output, execution)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        issue = type(error).__name__ + ":" + str(error)
        result = {"kind": "quartz_paired_control_observations", "scope": "ordinary_controls_only", "status": "invalid_attempt",
                  "execution": execution, "campaign_issues": [issue],
                  "pairs": [{"pair_id": pair["pair_id"], "case_ids": pair["case_ids"], "valid": False, "status": "invalid_control_pair", "issues": ["campaign_evidence_unavailable:" + issue], "branches": []} for pair in plan["pairs"]],
                  "primary_freeze_complete": False, "partial_repeat_policy": plan["partial_repeat_policy"]}
    write_new(output / "summary.json", json_bytes(result))
    print(json.dumps({"status": result["status"], "output": str(output)}))
    return 0 if result["status"] == "valid_control_pairs" else 1


if __name__ == "__main__":
    raise SystemExit(main())
