# Kanban ordinary controls closed, 17 November 2026 (Pacific)

Run 44212825790 at be80d8fa9199e6d65b246fcc260093e3fc714fc2 completed with all three arms setup_failed. Each exhausted application readiness before the browser or any workflow producer ran. No control.json exists. Independent evaluation cases and observed application defects: zero; this does not establish compatibility.

All three retained nginx container inspections show Running=true, requested 127.0.0.1:4200 to 80/tcp in HostConfig, but empty active NetworkSettings.Ports on the internal Docker network. Host readiness requests returned connection refused. The application startup logs report successful startup. These observations locate the failure at the harness connectivity boundary; they do not prove the entire application workflow works or fails. No extra diagnostic run was performed.

The one permitted infrastructure substitution had already replaced the unavailable OpenJDK image with the original Maven/JDK8 image. The controls freeze permits no further infrastructure correction. Kanban therefore remains in the original denominator as runtime-unqualified, with scientific variants not run. No replacement project or finding-driven rerun is added. Other reserved projects remain to be assessed.

All three archive SHA256 digests matched GitHub metadata before extraction. The prospective summary checker reports all_qualified=false. GitHub timing reports run_duration_ms=501000 and Ubuntu billable total_ms=0 for three jobs; this is service metadata, not a billing invoice. Authenticated image pulls succeeded in all arms. No paid model calls were made.
