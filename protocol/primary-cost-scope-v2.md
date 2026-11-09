# Prospective primary diagnostic cost scope, version 2

This amendment applies before primary freeze and boundary execution. It replaces the requirement for comparable exclusive phase costs in the initial equal-candidate diagnostic study. Normalization rules, historical timing records and later budgeted-selector requirements are unchanged.

The primary diagnostic cost measure is monotonic elapsed time for an independently reset branch, starting before reset/startup and ending after raw branch evidence capture/validation and confirmed owned-process teardown, immediately before serializing the controller summary. Include authentication, native browser work, application actions, shared verification, database backups where enabled, failures and cleanup. A completed interval is reported only when its end boundary is observed. Preserve interrupted or incomplete timing separately; do not impute a successful full interval from request durations or ISO timestamps.

Checkout, dependencies, build, common fixture construction and shared frontend startup remain separately disclosed common setup. Do not allocate them differently by continuation channel. Controller-summary serialization lies outside this interval and must not be relabelled as measured branch work. Nested operation, capture or teardown intervals are explanatory data and are never added again to the enclosing branch total. Summed request durations cannot substitute for elapsed branch time.

Cross-workflow exclusive-phase comparisons and isolated assigned-action speed claims are deferred. Existing phase records remain available descriptively under their own source-specific definitions. Direct route-cost comparisons require the same workflow, candidate, instrumentation/source version, runtime and cost boundary. Do not pool version 7 database-instrumented RealWorld timings with earlier uninstrumented timings. Across applications, report separate distributions rather than an aggregate speed ranking. Failed or shorter incomplete executions are attempted work, not successful speed improvements.

The later equal-budget selector experiment still needs fault-label-free calibration, the same effective pool and costs for all methods, and explicit deadline/overrun accounting. This amendment does not supply calibration, efficacy results or an execution budget for that experiment.

## Current implementation evidence

- RealWorld paired runner version 7 records monotonic `branches[].total_s` over reset, backend startup, adapter process, backend teardown and parent evidence validation. Its database-capture time is nested in adapter phases. This evidence covers the qualified identity diagnostic, not every remaining RealWorld route.
- Quartz paired runner version 2 records monotonic `cases[].elapsed_ms` from its per-case start through teardown. Adapter and startup subspans are nested and must not be summed with that total.
- PetClinic paired runner version 3 records direct request durations and wall-clock timestamps, but has no equivalent monotonic end-to-end branch interval. Add it prospectively in a new runner version and verify boundaries, failure retention and cleanup accounting on exposed controls. Do not reconstruct it by adding request times.

P4 remains open until every selected prospective path implements the registered measure and the primary preflight enforces that contract. Individual failed or interrupted attempts may record unavailable/incomplete timing with a reason; an intentionally uninstrumented path does not meet the gate. Reuse unchanged lifecycle qualification; test the new timing boundary rather than launching another blanket control campaign.
