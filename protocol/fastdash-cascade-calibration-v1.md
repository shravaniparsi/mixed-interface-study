# Fast Dash cascade calibration v1

Lead 5 of the frozen historical expansion. Outcome-exposed development calibration: issue 191 and the repair were read before design. No novelty, prevalence or unseen efficacy claim.

## Admission and state boundary

Admitted for cross-request application-state persistence, not disk durability. MCPState.inputs is a real server-side object used across tool requests and fresh request clients; independently copy that object before/after calls, and compare describe_app readbacks. This is consistent with the earlier shared-memory SQLite experiments' lack of restart durability. The storage boundary is explicitly different: no database rows, no browser, no crash/restart test. If direct object snapshots and fresh-client readbacks cannot be obtained, exclude the case rather than substitute mocked state.

The historical README documents that a list-returning depends_on resolver changes child options and clears its value. The MIT-licensed source is pinned to b2a27d5075f9fb6f042681e2eb72ca1587122983 and repair d1172129268042725a8bca517175799ed9860989. The repair batches eight issues. This experiment tests only the dependent-dropdown symptom across versions; it cannot isolate all changes in that commit or count eight defects.

## Eight executions

Two versions × four cases, each in a fresh process to respect the process-global MCP registry. Real FastDash instance, native Dash MCP Flask route and actual callback. Use the documented country/state resolver, plus an independent label string. Set country=India and state=Karnataka in separate successful calls before the operation.

- parent_change: set country=USA; child must clear to None; label remains original.
- label_edit: set label=edited; country and child remain India/Karnataka.
- explicit_clear: set child=None; country and label remain unchanged.
- already_clear: clear child during setup, then set country=USA; child remains None.

The framework's clear validation is a qualification condition. If it rejects None, preserve the failure and do not silently replace the control. Capture the advertised schemas, inputs, raw responses, direct state snapshots, describe_app before/after, and a readback using a fresh Flask client. Finally call invoke and get_invocation to record what the real callback consumed/returned. No browser-equivalence claim is made.

## Frozen baseline obligations

Validate operation arguments against captured set_input schema. Score operation success, the requested field's postcondition, unrelated-field preservation, and the documented dependent clear separately. The competent contract baseline includes the cascade; it is not a new algorithm. Also score naive preservation of all unnamed fields, expected to miss a stale child and potentially flag a correct cascade. Options-membership checks allow None. All scores are reconstructed from raw data, not supplied by the observer.

A result qualifies only if setup values match, successful ordinary label edit preserves its unrelated values, and independent snapshots agree with current-value readbacks. No population false-positive rate or independent sample size is inferred from controls. Cross-request readbacks and invoke observations are from the same case, not extra independent executions.

## Environment and attempts

Use Python 3.12.16. One environment job resolves the historical pyproject dependency list with Dash 4.4.1 and MCP 2.0.0 (the reported environment's versions) plus jsonschema 4.23.0, freezes all actual third-party versions before application cases execute, and supplies the identical lock to both version jobs. Import fast_dash directly from each pinned checkout; do not repackage or patch production source. Record package freeze and source blobs. Runtime dependency resolution is not described as known at protocol registration.

One three-job initial workflow, each job limited to 15 minutes. At most one separately registered instrument correction; no scientific request/oracle changes. Stop under the parent expansion's 100 aggregate job-minute ceiling. Existing expansion cost before this dispatch is 4.6 elapsed job-minutes. No paid model calls.
