# Registered experiments completed, 10 November 2026

The original diagnostic collection and all policy-selected repetitions are complete. The separate corrected Quartz collection now covers all 22 declared cases: six executed before the private Actions billing restriction and sixteen in a separately qualified public-host recovery cohort. No additional repetitions are selected by the corrected outcomes. The completion verifier reports zero remaining registered units.

## Corrected Quartz results

| Collection | Cases | Clean observations | Matched rejections | Unresolved policy | Eligible check mismatches |
|---|---:|---:|---:|---:|---:|
| First corrected attempt, private two-core host | 6 | 2 | 4 | 0 | 0 |
| Additional recovery, public four-core host | 16 | 12 | 1 | 3 | 0 |
| Disjoint case coverage | 22 | 14 | 5 | 3 | 0 |

This is a coverage inventory, not a pooled estimate from independent samples or a comparison of host performance. The recovery recorded 32 paired observations (candidate and reference in each unit), comprising 64 branch intervals. All sixteen units completed and independently reconstructed. Second repetitions selected: zero; third repetitions required: zero.

The unresolved cases are blank map keys, post-trim duplicate keys, and surrounding spaces in keys. Their observed continuation or preservation differences remain outside the registered normative assertions. They are not counted as defects or clean observations. The eight original nonempty-map comparisons affected by the form-reader bug remain measurement-invalid; later corrected observations do not rewrite the original data.

## Execution and evidence

- Public qualification: run 42867574418, source 89706dfef84e6dd78d5fe69d3cbfd7211bcd46f0; four clean pairs and eight populated form views independently verified.
- Recovery source release: successful CI 42868227122 and `manifests/quartz-recovery-freeze-v2.json`.
- Dispatch failure 42868555205 is retained with provider records and logs. The workflow called a v1 matrix entry point; selection failed and the application job was skipped without a runner or steps. No application case started.
- The separate dispatch amendment corrects all three entry points to v2 and checks its own workflow hash and successful source CI 42869036214. The frozen case payloads, environment, runtime, and outcome policy did not change.
- Recovery execution: run 42869295668, source 0cc8d0f0e301098998f65dd4aea0f002430a47bb, successful source CI 42869296523. All sixteen artifacts are retained under `results/quartz-recovery-v2-initial-ci-42869295668`.
- `manifests/quartz-recovery-execution-repeat2-v2.json` records the empty follow-up selection.
- `manifests/quartz-recovery-results-v2.json` contains independently reconstructable descriptive results.
- `manifests/experiment-completion-v3.json` links the original collection, incomplete provider attempt, public qualification, dispatch amendment, and additional recovery.

Run `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 scripts/build_experiment_completion_v3.py --verify` to reconstruct the completion record. CI performs the same verification.

## Research interpretation

The original 75 units and 26 selected repeat units are preserved, including semantic halts and unresolved outcomes. After excluding the eight invalid Quartz measurements, one original eligible UI-only check mismatch remains: the PetClinic hyphenated-owner-name continuation, observed across three repetitions. Repetition does not establish multiple independent defects. The corrected Quartz cases add no eligible mismatch finding.

Completion of this registered experiment package does not establish human defect adjudication, population generalization, selector efficacy, or journal submission readiness. The next research decision is whether the verified evidence supports a sufficiently strong contribution; the earlier nine-mismatch count must not be presented as nine defects.

The public standard-runner execution used no paid model API calls. No exact account bill is claimed.
