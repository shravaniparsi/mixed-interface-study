# Vibe Testing per-test transition pilot v1

## Question and limits

On the same fresh executions, does the published aggregate-count mutation rule disagree with evidence that an individually identified test passed on the original program and failed on a mutant? This is a measurement pilot using established paired-test reasoning, not a new mutation-testing principle. Neither rule alone establishes violation of an intended business requirement. Assertion failures, client exceptions, setup failures and 5xx responses remain distinguishable in the raw data.

All released outcomes and mutation definitions are exposed. Select all five archived models at L0 and L4, repetition 1: ten suites. This deterministic context-extreme selection is outcome-exposed and exploratory; no population rank or superiority claim follows. Use archived suites and application bytes unchanged. No model calls, repairs, regenerated tests, assertion removal or source fixes.

## Trial inventory

For each selected suite, in sorted source-path order within its context job: original control before, all 15 unchanged worker-defined operators in their archived order, original control after. Each mutation is applied once to pristine crud.py. An absent substitution is recorded without execution. A syntax-invalid variant is recorded without application startup. All 13 parseable applied variants are retained, including the docstring-only change. Planned inventory: 170 records, of which 150 can execute (20 original controls and 130 mutant trials).

A new process and fresh disposable SQLite files are used for every execution. Require /health=200, checked POST /reset, zero rows in all non-internal SQLite tables, recorded server PID and imported source hash. Disable bytecode writing and do not import cached app code. Stop and reap each process group. Preserve full pytest/JUnit reports, per-test stage reports, HTTP events, source hashes, dependency inventory and service logs. HTTP tracing rejects requests outside localhost/loopback port 8000. Generated suite code remains unchanged.

Run pytest with an outer 60-second process-group timeout. Do not add per-test timeouts or modify assertions. Timeout, collection failure, absent report, unavailable startup, reset failure and missing test identities receive no semantic-detection credit. If the before-control has no passing test or cannot produce usable evidence, record the remaining suite mutants as not executed and retain the after-control. Do not stop merely because some original tests fail; this is explicitly the condition being studied.

## Paired analyses

Reconstruct the published aggregate rule from before-control and mutant passed/failed/error counts. Independently align per-test IDs across before, mutant and after. Report tests that pass both original controls but fail on the mutant; separate assertion failures from exceptions and setup/teardown errors. Report original-control instability, missing test IDs and differences in collection. Never treat missing identities or censored executions as passed tests.

Report the complete ten-suite matrix, discrepancies in both directions, raw failing nodes, failure mechanisms and all exclusions. A count-rule disagreement is not automatically a false semantic credit: the target business property still needs adjudication. A matching count rule does not demonstrate absence of other evaluation problems. No ranking significance tests with one repetition. No claims about a model's current version: these are the frozen published suites.

## Bounds

Two standard Ubuntu jobs, one for L0 and one for L4, max-parallel 1, hard limit 20 minutes each and collection soft limit 17 minutes. Maximum 40 application-job minutes, zero paid model calls. At soft limit preserve every completed record and enumerate unattempted keys. No automatic rerun or correction is registered. The wider two-week feasibility gate and $20 pilot/$100 project ceilings remain unchanged.
