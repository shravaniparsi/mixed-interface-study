"""Mocked process ownership/termination tests; these never launch a browser."""

import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


WORKER_PATH = Path(__file__).resolve().parents[1] / "scripts/realworld_case_worker.py"
SPEC = importlib.util.spec_from_file_location("realworld_case_worker_cleanup_test", WORKER_PATH)
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)
MARKER = "--codex-study-case=" + "a1" * 10


def process(pid=101, parent=1, command=None, start="Fri Nov 6 12:00:00 2026"):
    return {"pid": pid, "parent": parent, "start": start,
            "command": command if command is not None else "/Chrome " + MARKER}


class Clock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def sleep(self, duration):
        self.value += duration


class BrowserCleanupTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "browser-pid.json"
        self.path.write_text(json.dumps({"pid": 101, "marker": MARKER}))
        self.clock = Clock()

    def cleanup(self):
        return worker.cleanup_browser(self.path, term_timeout=.1, kill_timeout=.1,
                                      poll_interval=.025, clock=self.clock, sleep=self.clock.sleep)

    def test_absent_metadata_means_browser_not_launched_after_launcher_exit(self):
        self.path.unlink()
        with patch.object(worker, "_browser_process_snapshot") as snapshot:
            result = self.cleanup()
        self.assertTrue(result["ok"])
        self.assertEqual(result["reason"], "browser_not_launched")
        snapshot.assert_not_called()

    def test_present_invalid_metadata_never_signals_or_claims_success(self):
        bad_records = ["{", "[]", json.dumps({"pid": 101, "marker": MARKER + "suffix"}),
                       json.dumps({"pid": "101", "marker": MARKER}),
                       json.dumps({"pid": True, "marker": MARKER}),
                       json.dumps({"marker": MARKER})]
        with patch.object(worker, "_browser_process_snapshot") as snapshot, patch.object(worker.os, "kill") as kill:
            for text in bad_records:
                self.path.write_text(text)
                self.assertFalse(self.cleanup()["ok"])
        snapshot.assert_not_called()
        kill.assert_not_called()

    def test_null_pid_marker_fallback_uses_exact_token_and_preserves_other_browser(self):
        self.path.write_text(json.dumps({"pid": None, "marker": MARKER}))
        live = {101: process(), 202: process(202, command="/Chrome " + MARKER + "suffix"),
                303: process(303, command="/Chrome --normal-user-profile")}
        def kill(pid, sig):
            self.assertEqual((pid, sig), (101, signal.SIGTERM))
            live.pop(pid)
        with patch.object(worker, "_browser_process_snapshot", side_effect=lambda **kw: dict(live)), patch.object(worker.os, "kill", side_effect=kill):
            result = self.cleanup()
        self.assertTrue(result["ok"])
        self.assertEqual(set(live), {202, 303})
        self.assertEqual(result["observed_owned_pids"], [101])

    def test_marker_appearing_after_initial_empty_scan_is_cleaned(self):
        self.path.write_text(json.dumps({"pid": None, "marker": MARKER}))
        live = {101: process()}
        calls = []
        def snapshot(**kwargs):
            calls.append(1)
            return {} if len(calls) == 1 else dict(live)
        with patch.object(worker, "_browser_process_snapshot", side_effect=snapshot), patch.object(worker.os, "kill", side_effect=lambda pid, sig: live.pop(pid)):
            result = self.cleanup()
        self.assertTrue(result["ok"])
        self.assertEqual(result["observed_owned_pids"], [101])

    def test_pid_reuse_between_scan_and_signal_is_not_targeted(self):
        calls = []
        replacement = process(command="/Chrome --unrelated", start="Fri Nov 6 12:01:00 2026")
        def snapshot(**kwargs):
            calls.append(1)
            return {101: process()} if len(calls) == 1 else {101: replacement}
        with patch.object(worker, "_browser_process_snapshot", side_effect=snapshot), patch.object(worker.os, "kill") as kill:
            result = self.cleanup()
        self.assertTrue(result["ok"])
        self.assertIn(101, result["identity_changes_skipped"])
        kill.assert_not_called()

    def test_orphaned_unmarked_descendant_is_retained_and_escalated(self):
        live = {101: process(), 102: process(102, 101, "/Chrome Helper --type=renderer"),
                303: process(303, command="/Chrome --unrelated")}
        def kill(pid, sig):
            if pid == 101:
                live.pop(pid)
                live[102] = dict(live[102], parent=1)
            elif sig == signal.SIGKILL:
                live.pop(pid)
        with patch.object(worker, "_browser_process_snapshot", side_effect=lambda **kw: dict(live)), patch.object(worker.os, "kill", side_effect=kill):
            result = self.cleanup()
        self.assertTrue(result["ok"])
        self.assertEqual(set(live), {303})
        self.assertEqual(result["observed_owned_pids"], [101, 102])
        self.assertIn({"pid": 102, "signal": "SIGKILL"}, result["signals"])
        self.assertEqual(result["remaining_owned_pids"], [])

    def test_reused_descendant_pid_after_reparenting_is_not_signalled(self):
        calls = []
        child = process(102, 101, "/Chrome Helper --type=renderer")
        live = {101: process(), 102: child}
        def snapshot(**kwargs):
            calls.append(1)
            if len(calls) == 2:
                live[102] = process(102, 1, "/Chrome Helper --unrelated", "Fri Nov 6 12:02:00 2026")
            return dict(live)
        def kill(pid, sig):
            self.assertEqual(pid, 101)
            live.pop(pid)
        with patch.object(worker, "_browser_process_snapshot", side_effect=snapshot), patch.object(worker.os, "kill", side_effect=kill):
            result = self.cleanup()
        self.assertTrue(result["ok"])
        self.assertEqual(set(live), {102})
        self.assertIn(102, result["identity_changes_skipped"])

    def test_parent_retry_recovers_orphan_identity_after_interrupted_cleanup(self):
        live = {101: process(), 102: process(102, 101, "/Chrome Helper --type=renderer")}
        interrupted = []
        def kill(pid, sig):
            if pid == 101:
                live.pop(pid)
                live[102] = dict(live[102], parent=1)
                interrupted.append(True)
                raise KeyboardInterrupt("simulate worker killed during cleanup")
            if sig == signal.SIGKILL:
                live.pop(pid)
        with patch.object(worker, "_browser_process_snapshot", side_effect=lambda **kw: dict(live)), patch.object(worker.os, "kill", side_effect=kill):
            with self.assertRaises(KeyboardInterrupt):
                self.cleanup()
            self.assertTrue(interrupted)
            ownership = self.path.with_name(self.path.name + ".owned.json")
            self.assertEqual({item["pid"] for item in json.loads(ownership.read_text())["processes"]}, {101, 102})
            self.assertNotIn("/Chrome", ownership.read_text())
            result = self.cleanup()
        self.assertTrue(result["ok"])
        self.assertEqual(live, {})
        self.assertIn({"pid": 102, "signal": "SIGKILL"}, result["signals"])

    def test_invalid_persistent_ownership_is_not_trusted(self):
        ownership = self.path.with_name(self.path.name + ".owned.json")
        ownership.write_text(json.dumps({"marker": MARKER, "processes": [{"pid": 303}]}))
        with patch.object(worker, "_browser_process_snapshot") as snapshot, patch.object(worker.os, "kill") as kill:
            result = self.cleanup()
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "invalid_ownership_snapshot")
        snapshot.assert_not_called()
        kill.assert_not_called()

    def test_sigkill_escalation_and_final_confirmation_are_required(self):
        live = {101: process()}
        def kill(pid, sig):
            if sig == signal.SIGKILL:
                live.pop(pid)
        with patch.object(worker, "_browser_process_snapshot", side_effect=lambda **kw: dict(live)), patch.object(worker.os, "kill", side_effect=kill):
            result = self.cleanup()
        self.assertTrue(result["ok"])
        self.assertEqual([item["signal"] for item in result["signals"]], ["SIGTERM", "SIGKILL"])
        self.assertGreaterEqual(result["elapsed_s"], .1)

    def test_process_that_survives_kill_is_unconfirmed_with_bounded_wait(self):
        with patch.object(worker, "_browser_process_snapshot", return_value={101: process()}), patch.object(worker.os, "kill"):
            result = self.cleanup()
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "owned_processes_remain")
        self.assertEqual(result["remaining_owned_pids"], [101])
        self.assertLessEqual(result["elapsed_s"], .201)

    def test_ps_failure_before_or_after_signal_is_not_success(self):
        for fail_after in (0, 2):
            calls = []
            def snapshot(**kwargs):
                if len(calls) >= fail_after:
                    raise RuntimeError("ps failed")
                calls.append(1)
                return {101: process()}
            with patch.object(worker, "_browser_process_snapshot", side_effect=snapshot), patch.object(worker.os, "kill"):
                result = self.cleanup()
            self.assertFalse(result["ok"])
            self.assertEqual(result["reason"], "process_enumeration_unconfirmed")
            self.assertEqual(result["error_type"], "RuntimeError")
            self.assertEqual(result["enumeration_timeout_count"], 0)

    def test_transient_timeout_requires_two_new_successful_empty_scans(self):
        events = iter(("empty", "timeout", "empty", "empty"))
        calls = []
        def snapshot(timeout):
            event = next(events)
            calls.append(event)
            if event == "timeout":
                self.clock.sleep(timeout)
                raise subprocess.TimeoutExpired("ps", timeout)
            return {}
        with patch.object(worker, "_browser_process_snapshot", side_effect=snapshot), patch.object(worker.os, "kill") as kill:
            result = self.cleanup()
        self.assertTrue(result["ok"])
        self.assertEqual(calls, ["empty", "timeout", "empty", "empty"])
        self.assertEqual(result["enumeration_timeout_count"], 1)
        self.assertEqual(result["error_type"], "TimeoutExpired")
        self.assertEqual(result["empty_scan_streak"], 2)
        self.assertEqual(result["successful_enumerations"], 3)
        kill.assert_not_called()

    def test_persistent_enumeration_timeouts_fail_within_existing_phase_budgets(self):
        allowances = []
        def snapshot(timeout):
            allowances.append(timeout)
            self.clock.sleep(timeout)
            raise subprocess.TimeoutExpired("ps", timeout)
        with patch.object(worker, "_browser_process_snapshot", side_effect=snapshot), patch.object(worker.os, "kill") as kill:
            result = self.cleanup()
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "process_enumeration_unconfirmed")
        self.assertEqual(result["error_type"], "TimeoutExpired")
        self.assertEqual(result["enumeration_timeout_count"], 2)
        self.assertEqual(result["successful_enumerations"], 0)
        self.assertEqual(result["empty_scan_streak"], 0)
        self.assertEqual(allowances, [.1, .1])
        self.assertLessEqual(result["elapsed_s"], .201)
        kill.assert_not_called()

    def test_identity_recheck_timeout_does_not_signal_using_stale_snapshot(self):
        events = iter(("owned", "timeout", "empty", "empty"))
        def snapshot(timeout):
            event = next(events)
            if event == "timeout":
                self.clock.sleep(timeout)
                raise subprocess.TimeoutExpired("ps", timeout)
            return {101: process()} if event == "owned" else {}
        with patch.object(worker, "_browser_process_snapshot", side_effect=snapshot), patch.object(worker.os, "kill") as kill:
            result = self.cleanup()
        self.assertTrue(result["ok"])
        self.assertEqual(result["enumeration_timeout_count"], 1)
        self.assertEqual(result["empty_scan_streak"], 2)
        kill.assert_not_called()

    def test_phase_end_does_not_schedule_tiny_timeout_or_extra_post_deadline_scan(self):
        allowances = []
        def snapshot(timeout):
            allowances.append(timeout)
            if len(allowances) == 1:
                self.clock.sleep(.09)
            return {}
        with patch.object(worker, "_browser_process_snapshot", side_effect=snapshot):
            result = self.cleanup()
        self.assertTrue(result["ok"])
        self.assertEqual(allowances, [.1, .1])
        self.assertEqual(result["enumeration_timeout_count"], 0)
        self.assertGreaterEqual(result["elapsed_s"], .1)

    def test_permission_failure_cannot_be_reported_as_exit(self):
        with patch.object(worker, "_browser_process_snapshot", return_value={101: process()}), patch.object(worker.os, "kill", side_effect=PermissionError):
            result = self.cleanup()
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "owned_process_signal_failed")

    def test_snapshot_requires_success_and_valid_rows(self):
        output = "101 1 Fri Nov  6 12:00:00 2026 /Applications/Google Chrome " + MARKER + "\n"
        with patch.object(worker.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=output)) as run:
            parsed = worker._browser_process_snapshot()
        run.assert_called_once_with(["ps", "-ww", "-axo", "pid=,ppid=,lstart=,command="],
                                    capture_output=True, text=True, timeout=.25)
        self.assertEqual(parsed[101]["start"], "Fri Nov 6 12:00:00 2026")
        self.assertEqual(parsed[101]["parent"], 1)
        for result in (SimpleNamespace(returncode=1, stdout=""), SimpleNamespace(returncode=0, stdout="invalid")):
            with patch.object(worker.subprocess, "run", return_value=result), self.assertRaises(RuntimeError):
                worker._browser_process_snapshot()
        with patch.object(worker.subprocess, "run", side_effect=subprocess.TimeoutExpired("ps", .25)), self.assertRaises(subprocess.TimeoutExpired):
            worker._browser_process_snapshot()

    def test_nonfinite_limits_do_not_start_cleanup(self):
        with patch.object(worker, "_browser_process_snapshot") as snapshot:
            result = worker.cleanup_browser(self.path, term_timeout=float("inf"), clock=self.clock)
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "invalid_cleanup_limits")
        snapshot.assert_not_called()


if __name__ == "__main__":
    unittest.main()
