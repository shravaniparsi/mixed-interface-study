# Write-response, persistence and readback measurements, version 1

Status: prospective measurement contract with replay of three previously exposed API-only diagnostics. Application campaign adapters are not yet bound to this contract. Existing terminal policies, archived classifications and primary-study gates are unchanged.

## Unit and evidence

One record describes one identified producer request, on one branch, from its independently restored fixture. Bind the record to immutable job, candidate, channel, application revision, database engine/version, actor, request trace and source-qualified evidence hashes. Repetitions and related controls are separate records, not independent sample units. API-only diagnostics cannot supply channel comparisons.

A qualified loader must verify the fixture, actor, request identity, trace ordering, projection definition, snapshot provenance and cleanup before constructing measurements. The pure measurement function validates shape and derives comparisons; it does not qualify evidence. Hashes alone do not establish qualification.

## Separate observations

| Dimension | Record | Interpretation |
| --- | --- | --- |
| Producer response | Exact HTTP status, or missing response | An error does not establish rejection, rollback or unchanged state. A success does not establish valid state. |
| Committed state | Before, immediate post-response and optional post-restart projections | Each snapshot is observed, unreadable, missing or not planned. Compare only identical declared projections. |
| Readback | One explicit entry per planned endpoint and phase; status or unreadable/missing/not planned | Retain individual failures and successes; a 200 response alone does not establish semantic correctness. |
| Native continuation | Separately bound action, requirement checks and outcome | API readbacks cannot substitute for native UI edit/save or another registered continuation. |
| Requirement policy | Existing source-backed requirement or unresolved policy | State evidence cannot invent a product requirement. |

The immediate committed-state observation precedes diagnostic API reads and continuation actions. Use an independent committed-state reader, validated for the chosen database isolation semantics. Record the snapshot scope explicitly. API response payloads do not substitute for a database snapshot. Observe restart persistence only with an actual controlled stop/restart and another qualified snapshot; absent restart observations remain unknown. Retain teardown evidence and all failed attempts.

For complete before/after projections, report unchanged, requested patch observed, or other change. Also report whether intended values are present, independently of whether anything changed (a no-op may already contain them). Other change can include partial intended effects or additional changes; retain the projections and do not infer transaction atomicity from a subset of columns. Unreadable or missing snapshots yield unknown change, never unchanged. Restart equality concerns the declared projection only.

Readback plans enumerate endpoint identities and phases before execution. Missing planned reads cannot disappear from the denominator. An HTTP response failure is distinct from an unreadable body and from an unattempted request. Semantic response validation and native continuation remain separate workflow checks. This version's replay retains HTTP readback evidence and marks native continuation not measured.

## Relationship to terminal decisions and stability

Version 2 terminal precedence remains authoritative. Missing required evidence still halts; confirmed cleanup does not repair it. A complete database observation does not repair a missing required frontend observation. Supported application response failures remain semantically incomplete, even when a committed mutation is established. Shared failures receive no channel-exclusive credit. Unknown policy stays unknown.

Prospective paired integration must bind both channels, the same fixture and projection, declared continuation requirements, and reference controls before dispatch. For a stable complete semantic observation, preserve the existing requirement of three complete candidate observations and three clean accepted controls. Repeated failed responses may support a separately labelled mechanism pattern; they do not become complete semantic findings or stable primary defects. Do not retry in place, overwrite halted attempts, or resume a failed immutable campaign. This contract grants no new dispatch authorization.

## Current evidence and next integration

The source-qualified diagnostic archive in manifests/realworld-identity-database-integration.json supplies three single-execution API records. Null produced 422 with unchanged selected state; length60 produced 200 with the intended write; length61 produced 500 with the intended write. The observed post-response projections survived restart. All eight readbacks per case returned 200, 200 and 500 respectively. These are deployment-specific diagnostic observations, not prevalence estimates.

The replay script independently verifies the retained archive and builds a derived record without changing its source files. Next implement a versioned paired identity loader that declares snapshot and continuation requirements, qualifies negative paths using fixtures, and maps measurements to existing terminal decisions. Review remaining corpus bindings before primary freeze. No untouched boundary is run as part of this contract work.
