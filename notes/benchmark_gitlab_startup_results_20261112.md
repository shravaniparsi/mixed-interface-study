# GitLab startup qualification v1: host probe failed

Run 43168226517 at frozen head 15ab5131acd21630381ea3dacc0f3694a06d56f7 finished with failure after 1233 seconds (20.55 infrastructure job minutes). The immutable image pulled successfully. All 30 host-side /-/health probes raised URLError over the ten-minute observation window. The instrument did not retain the HTTP error status or transport reason, so these observations cannot distinguish HTTP rejection, port mismatch or network failure.

The container was running, not OOM-killed, and its image healthcheck reported healthy with exit code zero. Core services including PostgreSQL, Redis, Puma, nginx, Gitaly and Workhorse were running. GitLab version was 15.7.5. Root free disk after the run was 59,006,816,256 bytes. These facts do not meet the frozen host-readiness criterion and do not establish authentication or workflow qualification.

No scientific cases or paid model calls ran. The authentication job remains undispatched because its prerequisite failed. No experimental input or family is dropped or substituted. A single targeted infrastructure diagnostic is justified by disagreement between internal health and the host probe; it must be registered separately and preserve this failed attempt. Do not retrospectively call this run successful.

The retained container state included incidental help-page HTML from the image's healthcheck. Public evidence omits those Output strings, recording their hashes and the original file hash in a redaction record. State, health status, timestamps and exit codes are unchanged; the original file remains local. No task evaluator or frontend validation logic was inspected.
