# Legacy RealWorld job binding, version 8

This implementation selects the five remaining exposed pairs (title 150, title 151, whitespace title, duplicate partial update, duplicate full update) and two native-only controls (comment creation/deletion and profile bio edits). It includes the existing article-create and unique-article-update paired reference controls. There are nine jobs and sixteen branch slots. Selection copies full case objects from the hash-pinned development registry; it changes no payload, producer route, requirement policy or exposure label.

`realworld_legacy_jobs_v8.selection()` returns the exact input registry. `plan_for()` returns initial jobs only. The new per-job runner accepts only these jobs, restores the offline fixture per branch, retains raw evidence and reports monotonic branch elapsed time through evidence validation and backend teardown. Common fixture/frontend setup remains separate. The unchanged paired adapter and normalization helper are reused; existing archived sources are not edited.

The loader checks job, selection, source inventory, application revisions, branch order, reset identity and timing before extraction. Paired jobs use the existing conservative terminal reducer. Native-only jobs use the branch classifier but return a separate singleton record: no fabricated API branch, no paired terminal envelope, no discrepancy boolean and no paired-comparison eligibility. Shared API probes used to verify a native operation do not change its producer or continuation route.

The title policies remain unknown. Empty or unresolvable returned references and other incomplete paths must remain incomplete unless a new trace-qualified extractor explicitly supports them. This implementation does not certify every accepted/error path. It does not add database captures or make timing comparable to the database-instrumented v7 runner.

## Qualification still required

The ten initial unit tests exercise exact selection, altered payloads/policies/routes, reference binding, singleton cardinality, missing evidence and cleanup precedence. They do not execute an application or demonstrate successful native singleton extraction.

Next, add trace-qualified semantic fixtures for successful native controls and the title/duplicate reference paths, resolving extractor gaps without changing unknown policies or repairing input. Then implement a bounded supervisor and independent archive verifier for this mixed-cardinality selection. Singleton outcomes need explicit continue/halt accounting outside the paired repeat machinery. Retain interrupted and failed attempts; no automatic retry or resume. Perform hosted qualification only on this exposed selection. Primary batching, repeat integration and freeze remain separate gates.
