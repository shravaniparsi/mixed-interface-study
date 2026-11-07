"""Pure/synthetic paired-control tests: no application or boundary execution."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

import test_quartz_oracle_components as fixtures


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
try:
    spec = importlib.util.spec_from_file_location("quartz_pairs", PROJECT / "scripts/run_quartz_pairs.py")
    pairs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pairs)
finally:
    sys.path.pop(0)
REGISTRY = json.loads((PROJECT / "manifests/quartz-job-generated-pool-v2.json").read_text())
CASES = {case["case_id"]: case for case in REGISTRY["cases"]}


def synthetic_case(case, directory):
    route = "-".join(operation["interface"] for operation in case["operations"])
    result, run = fixtures.positive(route)
    producer = copy.deepcopy(case["operations"][0]["input"])
    job = {"jobKeyDTO": {"group": "RESEARCH", "name": "pilot-job"}, "jobClassName": producer["jobClass"],
           "description": producer["description"], "durable": producer["durable"],
           "requestsRecovery": producer["requestsRecovery"], "jobDataMap": producer["jobDataMap"], "triggerKeys": []}
    command = copy.deepcopy(case["operations"][1]["input"])
    final_job = {**job, "description": command["description"]}
    result.update(case_id=case["case_id"], registered_inputs=copy.deepcopy(case["operations"]), expected_producer=case["expectation"],
                  producer={"kind": "response", "status": 201, "request": producer, "body": copy.deepcopy(job)},
                  continuation={"kind": "response", "status": 200, "request": command, "body": final_job},
                  stored_prefix=copy.deepcopy(job), final_job=final_job, bindings={"path": pairs.components.JOB_PATH, "command": copy.deepcopy(command)})
    result["browser_version"] = "151.0.7922.34"
    result["post_producer_state"]["jobs"] = [copy.deepcopy(job)]
    result["final_state"]["jobs"] = [copy.deepcopy(final_job)]
    for name in ("initial_state", "post_producer_state", "final_state"):
        result[name + "_sha256"] = pairs.components.state_hash(result[name])
    run.update(case_id=case["case_id"], evidence_directory=str(directory), initial_state_sha256=result["initial_state_sha256"], final_state_sha256=result["final_state_sha256"], elapsed_ms=1.0, phase_cost_ms={"synthetic": 1.0})
    return result, run


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="quartz-pairs-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "environment.json").write_text(json.dumps({"synthetic_fixture": True, "node": {"output": "v20.20.2", "exit_code": 0}}))
        (self.root / "browser.json").write_text(json.dumps({"synthetic_fixture": True, "declared": {"browserVersion": "151.0.7922.34"}, "actual_version": "Google Chrome for Testing 151.0.7922.34", "executable": "/synthetic/chrome"}))
        self.output = self.root / "campaign"
        self.config = {"runtime": "/synthetic/runtime", "java": "/synthetic/java", "node": "/synthetic/node", "python": sys.executable,
                       "registry": str(PROJECT / "manifests/quartz-job-generated-pool-v2.json"), "output": str(self.output),
                       "playwright_module": "/synthetic/playwright", "chrome_executable": "/synthetic/chrome",
                       "environment_file": str(self.root / "environment.json"), "browser_info": str(self.root / "browser.json"), "port": 19965}
        with patch.object(subprocess, "Popen", side_effect=AssertionError("Plan preparation must not launch a process")):
            self.plan = pairs.prepare_plan(self.config, self.output)

    def test_actual_pool_has_two_exact_control_pairs_with_alternating_order(self):
        built = pairs.build_pairs(REGISTRY)
        self.assertEqual([x["producer_interface"] for x in built], ["api", "ui"])
        self.assertEqual([x["consumer_order"] for x in built], [["api", "ui"], ["ui", "api"]])
        self.assertEqual(["-".join(x["interface"] for x in CASES[cid]["operations"]) for pair in built for cid in pair["case_ids"]], ["api-api", "api-ui", "ui-ui", "ui-api"])
        self.assertEqual(len({cid for pair in built for cid in pair["case_ids"]}), 4)
        self.assertTrue(all(CASES[cid]["estimated_cost_s"] == 1.0 for pair in built for cid in pair["case_ids"]))

    def test_plan_exists_and_verifies_before_any_dispatch(self):
        self.assertFalse((self.output / "run").exists())
        self.assertFalse((self.output / "dispatch.json").exists())
        self.assertEqual(pairs.verify_plan(self.output, live_sources=True), self.plan)
        self.assertIn("protocol/paired-control-validation-v1.md", self.plan["sources"])
        self.assertEqual(self.plan["timeouts"], {"case_timeout_ms": 75000, "campaign_timeout_s": 330, "shutdown_grace_s": 110, "kill_confirmation_s": 5})

    def test_input_or_source_tampering_invalidates_plan(self):
        for relative in ("inputs/environment.json", "inputs/browser.json", "case-order.json", "sources/scripts/run_quartz_registry.mjs"):
            with self.subTest(relative=relative):
                path = self.output / relative
                before = path.read_bytes()
                path.write_bytes(before + b"\n")
                with self.assertRaises(ValueError):
                    pairs.verify_plan(self.output)
                path.write_bytes(before)

    def rewrite_plan(self, plan):
        data = pairs.json_bytes(plan)
        (self.output / "plan.json").write_bytes(data)
        (self.output / "plan.sha256").write_text(pairs.sha(data) + "\n")

    def test_pair_hash_membership_and_removed_source_entry_are_not_trusted(self):
        for change in ("pair_hash", "case_hash", "inventory", "mode"):
            with self.subTest(change=change):
                plan = copy.deepcopy(self.plan)
                if change == "pair_hash":
                    plan["pairs"][0]["pair_sha256"] = "0" * 64
                elif change == "case_hash":
                    plan["pairs"][0]["case_sha256"][plan["case_ids"][0]] = "0" * 64
                elif change == "inventory":
                    plan["sources"].pop("scripts/quartz_browser_cleanup.py")
                else:
                    plan["effective_options"]["mode"] = "all"
                self.rewrite_plan(plan)
                with self.assertRaises(ValueError):
                    pairs.verify_plan(self.output)
        self.rewrite_plan(self.plan)

    def test_changed_expectation_scope_or_prefix_is_rejected(self):
        for kind in ("expectation_scope", "producer_input"):
            registry = copy.deepcopy(REGISTRY)
            cid = self.plan["pairs"][0]["case_ids"][0]
            case = next(x for x in registry["cases"] if x["case_id"] == cid)
            if kind == "expectation_scope":
                case["expectation_scope"] = {"kind": "different"}
            else:
                case["operations"][0]["input"]["description"] = "changed"
            with self.assertRaises(ValueError):
                pairs.build_pairs(registry)

    def create_evidence(self):
        run_dir = self.output / "run"
        run_dir.mkdir()
        for source, archived in pairs.ARCHIVED_RUN_SOURCES.items():
            shutil.copyfile(self.output / "sources" / source, run_dir / archived)
        shutil.copyfile(self.output / "inputs/registry.json", run_dir / "executed-registry.json")
        shutil.copyfile(self.output / "case-order.json", run_dir / "executed-case-order.json")
        summary = {"status": "pass", "mode": "controls", "ended_at": "2026-11-07T00:00:00Z", "case_count": 4,
                   "node_version": "v20.20.2",
                   "adapter_sha256": pairs.components.ADAPTER_SHA256, "registry_sha256": pairs.components.REGISTRY_SHA256,
                   "runner_sha256": self.plan["sources"]["scripts/run_quartz_registry.mjs"], "equal_initial_state_hashes": True,
                   "effective_options": self.plan["effective_options"],
                   "ordering": {"source": "case_order_file", "case_ids": self.plan["case_ids"], "order_file_sha256": self.plan["inputs"]["case-order.json"]},
                   "runtime": {"artifacts": [{"file": str(Path(self.config["runtime"]) / name), "sha256": sha} for name, sha in self.plan["expected_runtime_artifacts"].items()]}, "cases": []}
        records, extracted = {}, {}
        for index, cid in enumerate(self.plan["case_ids"], start=1):
            directory = run_dir / f"{index:03d}-synthetic-control"
            directory.mkdir()
            result, run = synthetic_case(CASES[cid], directory)
            run["server_pid"] = 1000 + index
            (directory / "result.json").write_bytes(pairs.json_bytes(result))
            (directory / "run.json").write_bytes(pairs.json_bytes(run))
            summary["cases"].append(run)
            records[cid] = (result, run, directory)
            extracted[cid] = pairs.components.reduce_case(result, run, CASES[cid])
            self.assertTrue(extracted[cid]["execution_evidence_complete"], extracted[cid]["evidence_issues"])
        (run_dir / "summary.json").write_bytes(pairs.json_bytes(summary))
        return records, extracted, summary

    def test_complete_synthetic_campaign_is_two_valid_pairs(self):
        self.create_evidence()
        output = pairs.summarize_campaign(self.output, {"successful_exit": True})
        self.assertEqual(output["status"], "valid_control_pairs", output)
        self.assertEqual(len(output["pairs"]), 2)
        self.assertTrue(all(all(pair["comparisons"].values()) for pair in output["pairs"]))
        self.assertTrue((self.output / "components.json").exists())
        self.assertFalse(output["primary_freeze_complete"])

    def test_order_or_runtime_inventory_drift_invalidates_campaign(self):
        _, _, summary = self.create_evidence()
        summary["ordering"]["case_ids"] = list(reversed(summary["ordering"]["case_ids"]))
        summary["runtime"]["artifacts"].pop()
        (self.output / "run/summary.json").write_bytes(pairs.json_bytes(summary))
        output = pairs.summarize_campaign(self.output, {"successful_exit": True})
        self.assertEqual(output["status"], "invalid_attempt")
        self.assertIn("runner_ordering_differs_from_plan", output["campaign_issues"])
        self.assertIn("runtime_artifact_inventory_differs", output["campaign_issues"])
        self.assertTrue(all(not pair["valid"] for pair in output["pairs"]))

    def test_actor_prefix_state_and_intended_binding_mismatches_invalidate_pair(self):
        records, extracted, _ = self.create_evidence()
        pair = self.plan["pairs"][0]
        for change in ("actor", "initial", "producer_input", "prefix", "binding", "actual_payload", "directories", "same_pid"):
            with self.subTest(change=change):
                edited = copy.deepcopy(records)
                result, run, directory = edited[pair["case_ids"][1]]
                if change == "actor":
                    result["api_actor"]["username"] = "other"
                elif change == "initial":
                    result["initial_state"]["jobs"] = [{"unexpected": True}]
                elif change == "producer_input":
                    result["producer"]["request"]["description"] = "changed"
                elif change == "prefix":
                    result["stored_prefix"]["jobDataMap"] = {"changed": True}
                elif change == "binding":
                    result["bindings"]["command"]["requestsRecovery"] = True
                elif change == "actual_payload":
                    result["continuation"]["request"]["description"] = "not the intended edit"
                elif change == "directories":
                    edited[pair["case_ids"][1]] = (result, run, edited[pair["case_ids"][0]][2])
                else:
                    run["server_pid"] = edited[pair["case_ids"][0]][1]["server_pid"]
                output = pairs.pair_observations(pair, edited, extracted)
                self.assertFalse(output["valid"], change)
                self.assertEqual(output["status"], "invalid_control_pair")

    def test_missing_rejected_or_unfinished_branch_is_invalid_not_neither(self):
        records, extracted, _ = self.create_evidence()
        pair = self.plan["pairs"][0]
        cid = pair["case_ids"][1]
        for change in ("missing", "rejected", "unfinished", "runner_failure"):
            with self.subTest(change=change):
                edited, observations = copy.deepcopy(records), copy.deepcopy(extracted)
                if change == "missing":
                    edited.pop(cid)
                elif change == "rejected":
                    edited[cid][0]["accepted_prefix"] = False
                    edited[cid][0]["producer"]["status"] = 400
                elif change == "unfinished":
                    observations[cid]["execution_evidence_complete"] = False
                output = pairs.pair_observations(pair, edited, observations, ["runner_failure"] if change == "runner_failure" else [])
                self.assertFalse(output["valid"])
                self.assertNotIn("neither", json.dumps(output))

    def test_existing_attempt_is_not_overwritten_or_resumed(self):
        with self.assertRaises(FileExistsError):
            pairs.prepare_plan(self.config, self.output)

    def test_captured_environment_disagreement_invalidates_pairs(self):
        _, _, summary = self.create_evidence()
        summary["node_version"] = "v99.0.0"
        (self.output / "run/summary.json").write_bytes(pairs.json_bytes(summary))
        output = pairs.summarize_campaign(self.output, {"successful_exit": True})
        self.assertEqual(output["status"], "invalid_attempt")
        self.assertFalse(output["environment_checks"]["node_version_matches_capture"])
        self.assertTrue(all(not pair["valid"] for pair in output["pairs"]))

    def test_unidentified_or_mismatched_browser_capture_is_rejected_before_dispatch(self):
        (self.root / "browser.json").write_text(json.dumps({"declared": {"browserVersion": "151.0.7922.34"}, "actual_version": "Chrome 150.0.1.2", "executable": "/wrong/chrome"}))
        with self.assertRaises(ValueError):
            pairs.prepare_plan(self.config, self.root / "second-campaign")
        self.assertFalse((self.root / "second-campaign").exists())


class BoundedRunnerTests(unittest.TestCase):
    def test_timeout_and_nonzero_exit_are_never_success(self):
        with tempfile.TemporaryDirectory(prefix="quartz-pair-process-test-") as directory:
            root = Path(directory)
            failed = pairs.run_bounded([sys.executable, "-c", "raise SystemExit(3)"], root, root / "failed.log", timeout=2, grace=1, kill_wait=1)
            self.assertEqual(failed["returncode"], 3)
            self.assertFalse(failed["successful_exit"])
            timed = pairs.run_bounded([sys.executable, "-c", "import time; time.sleep(10)"], root, root / "timed.log", timeout=0.1, grace=1, kill_wait=1)
            self.assertTrue(timed["timed_out"])
            self.assertTrue(timed["exit_confirmed"])
            self.assertFalse(timed["successful_exit"])

    def test_forced_runner_kill_does_not_claim_descendant_cleanup(self):
        process = Mock(pid=123)
        process.wait.side_effect = [subprocess.TimeoutExpired("runner", 1), subprocess.TimeoutExpired("runner", 1), -9]
        with tempfile.TemporaryDirectory(prefix="quartz-pair-force-test-") as directory, patch.object(subprocess, "Popen", return_value=process):
            output = pairs.run_bounded(["synthetic-runner"], directory, Path(directory) / "forced.log", timeout=1, grace=1, kill_wait=1)
        process.terminate.assert_called_once()
        process.kill.assert_called_once()
        self.assertTrue(output["hard_kill"])
        self.assertFalse(output["successful_exit"])
        self.assertEqual(output["cleanup_confirmation"], "unconfirmed_after_runner_hard_kill")

    def test_exit_between_timeout_and_terminate_is_recorded_not_raised(self):
        process = Mock(pid=123)
        process.wait.side_effect = [subprocess.TimeoutExpired("runner", 1), 0]
        process.terminate.side_effect = ProcessLookupError("already exited")
        process.poll.return_value = 0
        with tempfile.TemporaryDirectory(prefix="quartz-pair-race-test-") as directory, patch.object(subprocess, "Popen", return_value=process):
            output = pairs.run_bounded(["synthetic-runner"], directory, Path(directory) / "race.log", timeout=1, grace=1, kill_wait=1)
        self.assertEqual(output["terminate_disposition"], "already_exited_before_signal")
        self.assertTrue(output["exit_confirmed"])
        self.assertFalse(output["successful_exit"])
        process.kill.assert_not_called()

    def test_exit_before_kill_still_requires_confirmed_wait(self):
        process = Mock(pid=123)
        process.wait.side_effect = [subprocess.TimeoutExpired("runner", 1), subprocess.TimeoutExpired("runner", 1), 0]
        process.kill.side_effect = ProcessLookupError("already exited")
        process.poll.return_value = 0
        with tempfile.TemporaryDirectory(prefix="quartz-pair-kill-race-") as directory, patch.object(subprocess, "Popen", return_value=process):
            output = pairs.run_bounded(["synthetic-runner"], directory, Path(directory) / "race.log", timeout=1, grace=1, kill_wait=1)
        self.assertEqual(output["kill_disposition"], "already_exited_before_signal")
        self.assertTrue(output["exit_confirmed"])
        self.assertFalse(output["successful_exit"])


if __name__ == "__main__":
    unittest.main()
