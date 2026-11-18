# Typed-persistence historical impact audit

The separate v2 persistence checker changes none of the eleven retained summary
measurements examined here. Eight are paired API/UI records in
manifests/realworld-paired-database-integration.json (four candidate inputs);
three are API-only username cases summarized in
manifests/realworld-identity-database-integration.json. These are historical
engineering observations, not eleven independent defects or new scientific cases.

The audit reconstructed the old measurement from saved projections and original
prefix payloads in realworld-identity-controls-v1.json, checked it against the
retained summary, and compared the same inputs with v2. It checks intended value
observation, selected projection change and restart preservation, including the
nested saved projections. Missing or not-planned observations remain unavailable.
The old and new outputs agree on all eleven records. This does not negate the
synthetically reproduced boolean/number equality defect in v1.

Both original raw evidence directories named by these integration manifests are
absent from this checkout. Their source summaries retain hashes, but this audit
did not independently reopen or verify the raw databases. Hashing a summary is
not a replacement for validating its underlying observations. The conclusion
is limited to these saved measurement inputs, not all historical executions.

A local results/manifests JSON text search for intended_values_observed found
one saved file containing full measurement outputs, the paired integration
manifest. The separate API-only integration summary was found through the
original replay script. The scan does not cover absent archives, other checkouts,
or every possible alternative representation. No global no-impact claim follows.

Historical code, callers and outputs remain unchanged. The corrected version is
available for future development use only. No application, database or browser
was started, and no scientific case or causal finding was added.

Reproduce the retained-summary check with:

    PYTHONDONTWRITEBYTECODE=1 python3 scripts/extension/audit_typed_persistence_impact_v1.py --verify

The output binds the input manifests, both checker versions, equality helper
and audit script with SHA256. It records unavailable raw directories explicitly.
The remaining development gate is a complete, prospectively specified browser
fixture that distinguishes continuation blocking from normalization, rejection,
authorization failures, stale state, extra writes and missing evidence. Passing
that fixture would qualify instrumentation, not establish natural defect counts
or Q1 readiness.
