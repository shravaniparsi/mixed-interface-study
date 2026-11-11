# Historical write-preservation calibration v1

Registered 2026-11-11 before execution. This is development calibration using a known, already-fixed defect. It is not new-defect discovery, a blinded holdout, ecosystem prevalence, or evidence of agent/model performance. It does not extend the completed independent-input cohort.

## Decision and scope

The completed 44-pair independent-input study found no incremental native-only detections. More repetitions of that cohort cannot establish the missing contribution. Exploratory issue/code screening identified application state loss and several existing argument-preservation fixes. A simple omission/null-preservation fix is therefore not our novelty claim.

Before proposing a larger benchmark, test whether a low-cost runner can preserve real state evidence and correctly localize a known defect across an MCP and direct-command path. The selected case is webern/tiller-sync issue 40, fixed by commit 3566bd3f09430ad573a41bc7a4b52725b8be6221. Its immediate parent dea54f939e388ab857d0f4923b27f5793f028e33 is the historical version. Both were selected after reading the report and patch. This is one known mechanism, regardless of execution count.

## Frozen cases and comparison

Run three fixtures on each version, through both the actual MCP SDK server/client dispatch and the direct command function. Each execution gets a fresh upstream TestEnv and SQLite database.

1. Imported transaction, original_order present, note changed to `study edited note`.
2. Transaction explicitly initialized with original_order NULL, note changed to the same value. This is a fixture-level no-order control, not a claim that an actual sync created this state.
3. Imported transaction, original_order present, note explicitly changed to the empty string. This checks that preserving old state does not prevent a requested clear.

Six executions per version, twelve total. Read the complete transaction row directly from SQLite before and after, independently of the application's transaction getter. The expected write set is exactly `note`, based on the exposed update-fields contract and chosen input. No after-the-fact allowances for other column changes. Every changed column is retained. Full JSON request, advertised tool schema, return value/status, and row snapshots are saved.

The MCP path uses the project's real rmcp dispatch over an in-memory duplex transport. SQLite and command handlers are real. There is no stdio/HTTP transport measurement, live Google Sheet, LLM, or external service call. No sync-up/down operation is invoked. Any ordering effect on an external sheet remains reported prior evidence, not our measurement.

Baselines: advertised JSON Schema validity; operation return success; requested note postcondition; and the competent full-row frame check (all other columns unchanged). The frame check is a baseline, not a proposed novel technique. Compare direct and MCP outcomes to localize whether this case is wrapper-specific. A match in both paths must not be reported as an MCP-only defect.

## Execution bounds and failure handling

Two GitHub Actions jobs, standard ubuntu-24.04, at most 25 minutes each, no paid model calls. Capture runner Rust/Cargo versions and Cargo.lock hashes; use `cargo --locked`. The runner toolchain is recorded rather than claimed prospectively pinned. Source commits are immutable. Inject only an additional test module; do not alter production behavior. Preserve every attempt, including compilation/instrument errors.

At most one correction dispatch is allowed for independently explained instrumentation/build faults; retain the failed attempt and document the correction. Do not modify inputs, expected write sets, or classification to obtain a positive result. No statistical inference or independent-defect inflation from repeats.

## Advance / stop gate

Advance only if all twelve executions are observable, both valid controls qualify, historical/fixed differences can be reconstructed from raw rows, and MCP/direct localization is unambiguous. This only establishes replay feasibility. A larger study still needs a frozen independent sampling frame, multiple real mechanisms and projects, explicit legitimate-cascade controls, comparison with existing preservation methods, and a contribution beyond rediscovering reported bugs. Failure to meet that contribution gate is a reason to stop or redesign, not to declare Q1 readiness.
