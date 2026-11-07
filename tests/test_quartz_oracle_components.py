"""Synthetic evidence tests; none execute Quartz or establish application facts."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("quartz_components", PROJECT / "scripts/summarize_quartz_oracle_components.py")
reducer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reducer)


def check(check_id, passed=True, scope="requirement"):
    return {"id": check_id, "passed": passed, "scope": scope, "detail": "synthetic"}


def positive(route="api-api"):
    producer, consumer = route.split("-")
    actor = {"username": "admin", "authorities": [{"authority": "ROLE_ADMIN"}]}
    state = {"scheduler": {"status": "STOPPED"}, "jobs": [], "triggers": []}
    checks = [check(x) for x in [
        "initial_state_inactive_scheduler", "post_producer_state_inactive_scheduler",
        "producer_status", "producer_response_matches_persisted_job", "producer_business_fields",
        "single_stored_resource", "continuation_status", "final_business_state",
        "update_response_matches_persisted", "fresh_native_final_read",
        "final_state_inactive_scheduler", "final_single_resource", "no_unregistered_browser_request",
    ]]
    checks.append(check("consumer_api_loaded_bound_state" if consumer == "api" else "consumer_ui_loaded_bound_state"))
    if consumer == "ui":
        checks.append(check("native_PUT_payload_matches_bound_intent"))
    if producer == "ui":
        checks.extend([check("native_create_form"), check("native_POST_payload_matches_bound_intent")])
    traces = [
        {"source": "direct_api", "method": "POST", "path": "/quartz-manager/auth/login"},
        {"source": "direct_api", "method": "GET", "path": "/quartz-manager/auth/whoami"},
        {"source": "direct_api" if producer == "api" else "ui_network", "method": "POST", "path": reducer.JOB_PATH},
        {"source": "direct_api" if consumer == "api" else "ui_network", "method": "PUT", "path": reducer.JOB_PATH},
    ] + [{"source": "direct_api", "method": "GET", "path": reducer.JOB_PATH} for _ in range(3 if consumer == "api" else 2)]
    forms = ["fresh_final_native_read"] + (["producer_form"] if producer == "ui" else []) + (["consumer_loaded", "consumer_before_submit"] if consumer == "ui" else [])
    ui_phases = ["final_read"] + (["producer"] if producer == "ui" else []) + (["continuation"] if consumer == "ui" else [])
    result = {
        "case_id": "synthetic:" + route, "route": route, "intervention": "route_only",
        "status": "pass", "completed": True, "accepted_prefix": True,
        "reached_continuation": True, "blocked": False, "timed_out": False,
        "eligible": True, "attempted": True, "policy_unresolved": False,
        "ended_at": "2026-11-07T00:00:00Z",
        "producer": {"kind": "response", "status": 201},
        "continuation": {"kind": "response", "status": 200},
        "expected_producer": {"outcome": "accept"}, "bindings": {"path": reducer.JOB_PATH},
        "stored_prefix": {}, "final_job": {}, "checks": checks, "trace": traces,
        "initial_state": copy.deepcopy(state), "post_producer_state": copy.deepcopy(state), "final_state": copy.deepcopy(state),
        "api_actor": actor, "actors": [{"interface": "api", "principal": actor}] + [{"interface": "ui", "phase": phase, "principal": actor} for phase in ui_phases],
        "ui_forms": [{"label": label, "values": {}} for label in forms],
        "page_errors": [], "blocked_requests": [], "consumption_observations": [{"consumer_interface": consumer}],
    }
    for label in ("initial_state", "post_producer_state", "final_state"):
        result[label + "_sha256"] = reducer.state_hash(result[label])
    run = {key: result[key] for key in ["case_id", "route", "status", "completed", "accepted_prefix", "reached_continuation", "blocked", "timed_out", "initial_state_sha256", "final_state_sha256", "ended_at"]}
    run.update({"child_exit": {"code": 0, "signal": None}, "node_cleanup": {"ok": True}, "java_cleanup": {"ok": True}, "browser_cleanup": {"ok": True}, "browser_process_absent": True, "application_port_released": True})
    return result, run


def find_check(result, check_id):
    return next(x for x in result["checks"] if x["id"] == check_id)


class ComponentAttributionTests(unittest.TestCase):
    def test_four_route_controls_have_separate_components(self):
        for route in ("api-api", "api-ui", "ui-api", "ui-ui"):
            with self.subTest(route=route):
                result, run = positive(route)
                output = reducer.reduce_case(result, run)
                self.assertTrue(output["execution_evidence_complete"], output["evidence_issues"])
                assigned = "assigned_api_continuation" if route.endswith("api") else "assigned_native_continuation"
                other = "assigned_native_continuation" if route.endswith("api") else "assigned_api_continuation"
                self.assertEqual(output["components"][assigned]["status"], "no_check_mismatch_observed")
                self.assertEqual(output["components"][other]["status"], "not_applicable")

    def test_shared_ui_failure_cannot_become_api_failure(self):
        result, run = positive()
        find_check(result, "fresh_native_final_read")["passed"] = False
        result["status"] = run["status"] = "source_expectation_mismatch"
        output = reducer.reduce_case(result, run)
        self.assertTrue(output["execution_evidence_complete"])
        self.assertEqual(output["components"]["assigned_api_continuation"]["status"], "no_check_mismatch_observed")
        self.assertEqual(output["components"]["shared_final_native_read"]["failed_check_ids"], ["fresh_native_final_read"])

    def test_policy_differences_do_not_hide_unrelated_required_mismatch(self):
        result, run = positive("api-ui")
        result["policy_unresolved"] = True
        result["status"] = run["status"] = "policy_unresolved"
        payload = find_check(result, "native_PUT_payload_matches_bound_intent")
        payload.update(passed=False, scope="unresolved_policy")
        result["checks"].append(check("raw_map_preservation_observation", False, "unresolved_policy"))
        find_check(result, "final_business_state")["passed"] = False
        output = reducer.reduce_case(result, run)
        self.assertTrue(output["execution_evidence_complete"], output["evidence_issues"])
        self.assertEqual(output["components"]["shared_post_continuation_api_readback"]["failed_check_ids"], ["final_business_state"])
        self.assertEqual(output["components"]["assigned_native_continuation"]["failed_check_ids"], [])
        self.assertEqual(set(output["components"]["unresolved_policy"]["failed_check_ids"]), {"native_PUT_payload_matches_bound_intent", "raw_map_preservation_observation"})
        self.assertFalse(output["components"]["unresolved_policy"]["comparison_eligible"])

    def test_case_status_cannot_override_failed_check(self):
        result, run = positive()
        find_check(result, "final_business_state")["passed"] = False
        output = reducer.reduce_case(result, run)
        self.assertEqual(output["components"]["shared_post_continuation_api_readback"]["status"], "check_mismatch_observed")

    def test_api_readback_after_native_action_is_not_native_only(self):
        result, run = positive("api-ui")
        find_check(result, "final_business_state")["passed"] = False
        output = reducer.reduce_case(result, run)
        self.assertTrue(output["execution_evidence_complete"])
        shared = output["components"]["shared_post_continuation_api_readback"]
        self.assertEqual(shared["assigned_action_interface"], "ui")
        self.assertEqual(shared["failed_check_ids"], ["final_business_state"])
        self.assertFalse(output["components"]["assigned_native_continuation"]["mismatch_observed"])

    def test_unknown_and_missing_checks_fail_closed(self):
        for alteration in ("unknown", "missing", "duplicate", "scope"):
            with self.subTest(alteration=alteration):
                result, run = positive()
                if alteration == "unknown":
                    result["checks"].append(check("future_unknown_check"))
                elif alteration == "missing":
                    result["checks"] = [x for x in result["checks"] if x["id"] != "consumer_api_loaded_bound_state"]
                elif alteration == "duplicate":
                    result["checks"].append(copy.deepcopy(result["checks"][0]))
                else:
                    find_check(result, "final_business_state")["scope"] = "unresolved_policy"
                output = reducer.reduce_case(result, run)
                self.assertFalse(output["execution_evidence_complete"])
                self.assertEqual(output["components"]["assigned_api_continuation"]["status"], "incomplete_or_invalid_evidence")

    def test_missing_native_form_and_request_evidence_fail_closed(self):
        for field in ("ui_forms", "trace", "actors"):
            with self.subTest(field=field):
                result, run = positive("api-ui")
                result[field] = []
                output = reducer.reduce_case(result, run)
                self.assertFalse(output["execution_evidence_complete"])

    def test_async_trace_phase_does_not_change_attribution(self):
        result, run = positive("ui-ui")
        before = reducer.reduce_case(result, run)
        for item in result["trace"]:
            item["phase"] = "arbitrary_later_phase"
        self.assertEqual(before, reducer.reduce_case(result, run))

    def test_unfinished_or_nonzero_exit_is_not_clean(self):
        for alteration in ("unfinished", "exit", "timeout", "run_incomplete", "cleanup", "reset"):
            with self.subTest(alteration=alteration):
                result, run = positive()
                if alteration == "unfinished":
                    result["completed"] = run["completed"] = False
                elif alteration == "exit":
                    run["child_exit"]["code"] = 1
                elif alteration == "timeout":
                    run["timed_out"] = True
                elif alteration == "cleanup":
                    run["browser_cleanup"]["ok"] = False
                elif alteration == "reset":
                    find_check(result, "initial_state_inactive_scheduler")["passed"] = False
                output = reducer.reduce_case(result, run, run_complete=alteration != "run_incomplete")
                self.assertFalse(output["execution_evidence_complete"])
                self.assertFalse(output["components"]["assigned_api_continuation"]["comparison_eligible"])

    def test_rejected_prefix_has_no_downstream_signal(self):
        result, run = positive()
        for data in (result, run):
            data.update(accepted_prefix=False, reached_continuation=False)
        result.update(producer={"kind": "response", "status": 400}, continuation={"attempted": False, "reason": "producer_not_accepted"},
                      expected_producer={"outcome": "reject"}, consumption_observations=[], ui_forms=[])
        result["actors"] = result["actors"][:1]
        result["checks"] = [check(x) for x in ["initial_state_inactive_scheduler", "post_producer_state_inactive_scheduler", "no_unregistered_browser_request", "rejected_prefix_left_empty_store", "rejected_prefix_full_state_unchanged", "producer_expectation"]]
        output = reducer.reduce_case(result, run)
        self.assertTrue(output["execution_evidence_complete"], output["evidence_issues"])
        self.assertEqual(output["components"]["assigned_api_continuation"]["status"], "not_reached_prefix_rejected")
        self.assertFalse(output["components"]["assigned_api_continuation"]["mismatch_observed"])
        result["checks"].append(check("continuation_status", False))
        invalid = reducer.reduce_case(result, run)
        self.assertFalse(invalid["execution_evidence_complete"])
        self.assertFalse(invalid["components"]["assigned_api_continuation"]["comparison_eligible"])
        self.assertFalse(invalid["components"]["assigned_api_continuation"]["mismatch_observed"])

    def test_wrong_interface_check_cannot_be_api_evidence(self):
        result, run = positive("api-ui")
        result["checks"].append(check("consumer_api_loaded_bound_state", False))
        output = reducer.reduce_case(result, run)
        self.assertFalse(output["execution_evidence_complete"])
        self.assertFalse(output["components"]["assigned_api_continuation"]["comparison_eligible"])

    def test_native_producer_check_cannot_be_api_producer_evidence(self):
        result, run = positive("api-api")
        result["checks"].append(check("native_create_form", False))
        output = reducer.reduce_case(result, run)
        self.assertFalse(output["execution_evidence_complete"])
        self.assertFalse(output["components"]["producer_native_controls"]["comparison_eligible"])
        self.assertFalse(output["components"]["producer_native_controls"]["mismatch_observed"])

    def test_rejected_branch_check_cannot_appear_on_accepted_prefix(self):
        result, run = positive()
        result["checks"].append(check("rejected_prefix_left_empty_store"))
        output = reducer.reduce_case(result, run)
        self.assertFalse(output["execution_evidence_complete"])
        self.assertIn("unexpected_check_for_execution_branch:rejected_prefix_left_empty_store", output["evidence_issues"])

    def test_edited_state_without_updated_hash_fails_closed(self):
        result, run = positive()
        result["post_producer_state"]["jobs"].append({"description": "edited evidence"})
        output = reducer.reduce_case(result, run)
        self.assertFalse(output["execution_evidence_complete"])
        self.assertIn("recorded_state_hash_mismatch:post_producer_state", output["evidence_issues"])

    def test_missing_state_hash_and_unsupported_float_fail_closed(self):
        result, run = positive()
        del result["post_producer_state_sha256"]
        result["final_state"]["jobs"].append({"outside_catalog_number": 0.1})
        output = reducer.reduce_case(result, run)
        self.assertFalse(output["execution_evidence_complete"])
        self.assertIn("missing_required_state_hash:post_producer_state", output["evidence_issues"])
        self.assertTrue(any(x.startswith("unverifiable_state_hash:final_state") for x in output["evidence_issues"]))

    def test_canonical_hash_preserves_types_and_utf16_key_order(self):
        value = {"\ue000": 7, "🌱": [True, None, "Café 東京"], "a": {"z": False}}
        expected = '{"a":{"z":false},"🌱":[true,null,"Café 東京"],"\ue000":7}'.encode()
        self.assertEqual(reducer.js_canonical_bytes(value), expected)
        self.assertEqual(reducer.js_canonical_bytes({"10": 10, "2": 2, "01": 1}), b'{"2":2,"10":10,"01":1}')
        self.assertNotEqual(reducer.state_hash({"x": 7}), reducer.state_hash({"x": "7"}))


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="quartz-component-test-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        shutil.copyfile(PROJECT / "scripts/quartz_generated_case.mjs", self.directory / "executed-adapter.mjs")
        shutil.copyfile(PROJECT / "manifests/quartz-job-generated-pool-v2.json", self.directory / "executed-registry.json")
        registry = json.loads((self.directory / "executed-registry.json").read_text())
        self.summary = {"mode": "controls", "status": "pass", "ended_at": "2026-11-07T00:00:00Z", "case_count": 4,
                        "adapter_sha256": reducer.ADAPTER_SHA256, "registry_sha256": reducer.REGISTRY_SHA256,
                        "equal_initial_state_hashes": True, "cases": []}
        for index, case in enumerate(c for c in registry["cases"] if c["intervention"] == "route_only"):
            route = "-".join(x["interface"] for x in case["operations"])
            result, run = positive(route)
            result.update(case_id=case["case_id"], registered_inputs=case["operations"], expected_producer=case["expectation"])
            run["case_id"] = case["case_id"]
            leaf = f"{index:03d}-{route}"
            run["evidence_directory"] = "/old/ci/location/" + leaf
            case_dir = self.directory / leaf
            case_dir.mkdir()
            (case_dir / "result.json").write_text(json.dumps(result))
            (case_dir / "run.json").write_text(json.dumps(run))
            self.summary["cases"].append(run)
        self.save_summary()

    def save_summary(self):
        (self.directory / "summary.json").write_text(json.dumps(self.summary))

    def test_pinned_relocated_evidence_is_supported(self):
        output = reducer.summarize_run(self.directory)
        self.assertEqual(output["status"], "complete_observations", output)
        self.assertEqual(output["case_count"], 4)

    def test_changed_or_missing_executed_adapter_is_rejected(self):
        path = self.directory / "executed-adapter.mjs"
        path.write_text(path.read_text() + "\n// source drift\n")
        self.assertEqual(reducer.summarize_run(self.directory)["status"], "incomplete_or_invalid_evidence")
        path.unlink()
        self.assertEqual(reducer.summarize_run(self.directory)["status"], "incomplete_or_invalid_evidence")

    def test_unsupported_summary_hash_is_rejected(self):
        self.summary["adapter_sha256"] = "0" * 64
        self.save_summary()
        output = reducer.summarize_run(self.directory)
        self.assertEqual(output["status"], "incomplete_or_invalid_evidence")
        self.assertIn("summary_pins_do_not_match_supported_evidence", output["run_issues"])

    def test_missing_case_cannot_be_a_completed_run(self):
        self.summary["cases"].pop()
        self.save_summary()
        output = reducer.summarize_run(self.directory)
        self.assertEqual(output["status"], "incomplete_or_invalid_evidence")
        self.assertTrue(all(not x["execution_evidence_complete"] for x in output["cases"]))

    def test_registry_input_drift_is_rejected(self):
        leaf = Path(self.summary["cases"][0]["evidence_directory"]).name
        path = self.directory / leaf / "result.json"
        result = json.loads(path.read_text())
        result["registered_inputs"][0]["input"]["description"] = "changed"
        path.write_text(json.dumps(result))
        output = reducer.summarize_run(self.directory)
        self.assertEqual(output["status"], "incomplete_or_invalid_evidence")
        self.assertIn("registry_mismatch:registered_inputs", output["cases"][0]["evidence_issues"])


if __name__ == "__main__":
    unittest.main()
