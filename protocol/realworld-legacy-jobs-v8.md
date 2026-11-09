# Legacy RealWorld job binding, version 8

This implementation selects the five remaining exposed pairs (title 150, title 151, whitespace title, duplicate partial update, duplicate full update) and two native-only controls (comment creation/deletion and profile bio edits). It includes the existing article-create and unique-article-update paired reference controls. There are nine jobs and sixteen branch slots. Selection copies full case objects from the hash-pinned development registry; it changes no payload, producer route, requirement policy or exposure label.

`realworld_legacy_jobs_v8.selection()` returns the exact input registry. `plan_for()` returns initial jobs only. The new per-job runner accepts only these jobs, restores the offline fixture per branch, retains raw evidence and reports monotonic branch elapsed time through evidence validation and backend teardown. Common fixture/frontend setup remains separate. The unchanged paired adapter and normalization helper are reused; existing archived sources are not edited.

The loader checks job, selection, source inventory, application revisions, branch order, reset identity and timing before extraction. Paired jobs use the existing conservative terminal reducer. Native-only jobs use the branch classifier but return a separate singleton record: no fabricated API branch, no paired terminal envelope, no discrepancy boolean and no paired-comparison eligibility. Shared API probes used to verify a native operation do not change its producer or continuation route.

The title policies remain unknown. Empty or unresolvable returned references and other incomplete paths must remain incomplete unless a new trace-qualified extractor explicitly supports them. This implementation does not certify every accepted/error path. It does not add database captures or make timing comparable to the database-instrumented v7 runner.

## Qualification still required

The ten initial unit tests exercise exact selection, altered payloads/policies/routes, reference binding, singleton cardinality, missing evidence and cleanup precedence. They do not execute an application or demonstrate successful native singleton extraction.

Next, add trace-qualified semantic fixtures for successful native controls and the title/duplicate reference paths, resolving extractor gaps without changing unknown policies or repairing input. Then implement a bounded supervisor and independent archive verifier for this mixed-cardinality selection. Singleton outcomes need explicit continue/halt accounting outside the paired repeat machinery. Retain interrupted and failed attempts; no automatic retry or resume. Perform hosted qualification only on this exposed selection. Primary batching, repeat integration and freeze remain separate gates.

## Native semantic regression qualification

The native singleton extractor now uses a versioned reducer that selects the comments-list response from the continuation phase. The earlier reducer selected the first native list response, which belongs to the producer page before creation and is empty. This made a supported comment-load check appear unsupported. No archived reducer or raw trace was edited.

Eight additional tests use byte-preserved native traces from hosted run 42401381642, artifact 13585144786. The fixture provenance lists all file hashes. Test envelopes explicitly change oracle revision to 3 and assume v8 completed transport and confirmed backend cleanup. These are synthetic semantic tests, not v8 live qualification. Both native success paths classify cleanly; missing continuation-phase lists, wrong comment identities and absent cleanup confirmation fail closed. Successful singletons remain ineligible for paired contrasts.

Next: qualify the title and duplicate-reference semantic paths, then add mixed-cardinality supervision and independent archive verification before hosted execution. New runner timing and cleanup remain unqualified.

## Article semantic qualification

Ten additional tests construct explicit synthetic scenarios from the retained paired-control traces. They bind the exact registered title strings and duplicate partial/full commands, preserve unknown policies, and exercise both API and UI success paths. Resource substitutions and canonical snapshot reconstruction occur only in test fixtures; they are not observed application results or input repairs in the runner.

The API failure-path tests distinguish an empty producer reference from a trace-supported continuation 404. An empty reference is an immediate-response mismatch and reaches neither continuation. Two such branches remain an incomparable pair with no channel-discrepancy claim because neither executed a consumer command. A 404 has an assigned HTTP observation; a missing response or a claimed status inconsistent with its trace remains missing evidence. Wrong duplicate targets and forged command bodies also fail closed.

This qualifies the listed synthetic semantic paths, not all browser failure behavior, live runner timing or cleanup. The accepted title success paths remain unresolved-policy observations. The next implementation step is a bounded mixed-cardinality campaign supervisor and independent archive verifier, followed by hosted execution of exposed cases only.
