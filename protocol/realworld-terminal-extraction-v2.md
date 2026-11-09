# RealWorld terminal extraction, implementation stage 1

This stage adds branch classification against the existing prospective-control adapter and component reducer. It starts no applications and does not qualify per-job dispatch or alter the retained corpus coverage map.

The owning loader must qualify source, registry, reset and artifact identity before invoking the pure classifier. Cleanup confirmation must come from the supervisor. Backend exit and explicit cleanup confirmation take precedence over all semantic observations. Interruption and timeout follow. Missing records, adapter exceptions, unexpected exits, unsupported runner states and incomplete evidence halt rather than becoming application findings.

The adapter exits zero for a completed observation even when business checks fail. The new runner status `completed` may therefore be translated to the historical reducer's `passed` transport label only after verifying raw completion and integer exit zero. Raw check values, trace data and the caller's records remain unchanged. The reducer independently checks command and state evidence. Complete, trace-supported expectation mismatches remain mismatches; unsupported verdict changes are incomplete evidence. Arbitrary exception messages containing HTTP statuses do not establish application-response failures.

The command `python scripts/realworld_terminal_outcomes.py results/realworld-paired-controls-ci-20261107` first invokes the existing source-qualified archive validator, then requires all fourteen archived controls to classify cleanly. This is historical replay, not a new lifecycle test or a new sample. CI retains its JSON output. Eighteen targeted tests cover the ordinary archive and synthetic counterexamples.

Next implementation stage: immutable per-job selection and branch order, pair comparability, supervisor-backed cleanup, terminal envelopes, reference-control repeat scheduling and fresh hosted controls. The current branch classifier alone must not be used to authorize campaign continuation. P2 remains open and the primary freeze remains incomplete.
