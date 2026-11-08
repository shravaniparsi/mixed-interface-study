# Primary experiment readiness audit — 8 November 2026

The primary experiment is **not frozen**. Five concrete blockers remain. Several older ledger statements describe checks that have since passed; this audit replaces those statements as the current backlog without changing historical evidence or excluding workflows.

## What is already supported

- The inventory registers eight workflow templates, 73 paired catalog entries and two singleton controls. These are not independent sample counts. Quartz contributes 22 pairs: two ordinary controls and 20 mutation pairs whose 40 branches remain unexecuted.
- Source-qualified control extraction and paired accounting exist across all three applications. The historical 38-branch analysis and newer 14-branch RealWorld cohort overlap; their counts must not be pooled as new independent observations.
- Rejected-state checks passed on **eight RealWorld and six PetClinic known-control branches**. The recorded API-visible state remained unchanged. The old claim that these checks still need to be implemented is stale for those qualified source versions. Coverage of changed, unreadable and unobserved outcomes in the final primary path still needs explicit treatment.
- Declared interruption probes and subsequent fresh controls passed for RealWorld, PetClinic and Quartz. Quartz also passed its ordinary 75-second deadline path with an injected adapter stall. These results qualify the tested paths and checkpoints. There is no reason to add another blanket lifecycle test campaign for unchanged paths.
- RealWorld tag membership/representation and profile omission/null rules are implemented and tested in its prospective controls. They do not automatically cover other profile fields, every native producer, or other applications.

The [machine-readable audit](../manifests/primary-readiness-audit-v1.json) pins the evidence and code used for these decisions.

## Exact remaining blockers

| ID | Current gap | Completion evidence |
| --- | --- | --- |
| P1 | Terminal-outcome and stop/repeat semantics disagree across layers. The planner accepts incomplete outcomes for diagnostic repetition after a complete sweep; the driver halts on every incomplete outcome; the Quartz wrapper raises before extraction on unsuccessful runner exit. | One versioned contract distinguishing complete mismatches, matched rejections, unresolved policy, trace-supported application failures, missing evidence, timeouts and infrastructure/cleanup failure. The protocol, extractor and driver must implement the same continue/repeat/halt decisions. Test all classes without tuning on untouched boundary cases. |
| P2 | Hosted primary paths remain restricted to controls. Quartz selects two control pairs, RealWorld permits only its one-pass engineering registry, and PetClinic uses a fixed integrity selection. | A complete retained-corpus map to runner, route, reference control, input/binding checks, rejection-state checks, normalization and extractor versions. Implement and validate missing paths on engineering evidence. Preserve exposure strata; do not invent extra routes or discard hard cases after seeing outcomes. |
| P3 | No bounded primary batching and aggregation plan exists. | An immutable campaign/batch/job/attempt manifest that fits CI limits, preserves failed attempts, checks source/environment consistency and produces deterministic follow-ups only after the declared initial sweep. Planned batches must be distinguishable from replacement of failed attempts. |
| P4 | The declared primary timing contract exceeds the shared instrumentation currently implemented. | Implement the registered exclusive phases across retained workflows **or prospectively amend the primary cost scope** to supported end-to-end measures and defer unsupported phase comparisons. In either case preserve failed work, common setup and nested timing boundaries. This decision comes before more instrumentation, not after boundary results. |
| P5 | No dated executable final freeze exists. | After P1–P4, freeze corpus/exposure strata, sources, requirements and unresolved-policy rubric, normalization, schedule/repeats, batches, timing scope, commands and runtime acceptance fields. Enforce these in preflight and run the final ordinary-control smoke. Reuse lifecycle evidence where the owned-process path is unchanged. |

## Why batching is a real blocker

The Quartz initial schedule has 44 branch slots. At the registered 75-second case allowance, those allowances total **3,300 seconds before teardown and common setup**. The current application step is limited to 540 seconds, and the Quartz wrapper has a 480-second outer limit. Each flagged pair adds eight branch slots for candidate repeats and accompanying controls.

This arithmetic describes the budget envelope, not measured execution time or a prediction that every case will time out. It establishes that simply enabling the full registry in the existing controls workflow would not provide a properly bounded campaign. The batches and aggregation rules must be registered first.

## Implementation order and stop conditions

1. **P1 first:** settle terminal records and continue/repeat/halt semantics. Keep complete application discrepancies available to analysis while stopping uncertain cleanup or infrastructure failure. Do not relabel missing evidence as a pass.
2. **P2:** bind all retained entries to exact executable contracts and add missing primary paths. This keeps the eight-workflow scope intact; any justified change requires a prospective amendment, not silent narrowing.
3. **P3:** implement immutable bounded batches and aggregation, including missing/failed-batch accounting and repeat scheduling. Do not enable untouched boundary execution during this engineering step.
4. **P4:** resolve the timing-scope decision and implement only what that registered primary question needs. This can proceed alongside P2/P3.
5. **P5:** issue the final freeze and preflight the complete intended campaign before boundary execution.

Changing an owned-process lifecycle, signal handling or deadline path requires relevant requalification. A documentation correction or batch-accounting change does not automatically require rerunning every historical application probe.

## Work that does not block descriptive primary observations

Timed selector efficacy, common-budget cost calibration and broader structural diversity belong to the later selector evaluation. They must not be smuggled into a diagnostic-overlap claim or used to keep the equal-candidate study indefinitely in preparation.

Confirmed defect labels, root-cause deduplication and prior-report classification require their own evidence before those claims are made. They need not be completed before collecting descriptive source-check observations. Unresolved policy stays explicit, and AI review is not human agreement or maintainer confirmation.

A Q1 submission still needs substantive results, defensible novelty and a well-supported manuscript. Passing controls or increasing the harness test count does not establish those contributions. This audit ran no applications, discovered no new defects and did not increase the study sample.
