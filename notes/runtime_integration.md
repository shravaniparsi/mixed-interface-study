# Executed runtime integration and third-application control

Completed 6 November 2026 Pacific time (7 November UTC). Additional cash spend: **$0**. All study services are stopped.

The generated-case registry now executes real native UI/API workflows under a common measured budget. Quartz Manager also passes one ordinary workflow across all four interface routes. These results establish experimental infrastructure and deployment feasibility. They do not establish a new defect, selector superiority, agent behavior, or Q1 publication readiness.

## Generated RealWorld execution

The unchanged 18-case article-create/body-edit pool was regenerated and checked against its saved canonical content. Every candidate ran from an independently restored fixture. Ten completed their application checks, six rejected the producer input, and two produced a server error at creation. All 18 completed as adapter executions. The two server-error cases are repeats of the previously examined 151-character title condition, not two new faults.

Actual UI payloads are compared with declared and output-bound inputs. The consumer changes only the body while preserving accepted producer fields. The shared final API and fresh native UI checks apply to every successful route; oracle-only reads earn no route coverage. Rejected producers earn no consumer dependency coverage.

Eight valid controls, two per route, supplied these median total case costs. Reset, startup, authentication, operations, checks, evidence capture and teardown are included. Fixture construction and frontend startup are shared setup outside the budget.

| Route | Median seconds |
| --- | ---: |
| ui-ui | 3.137 |
| api-ui | 2.502 |
| ui-api | 2.757 |
| api-api | 1.952 |

The registered budget formula, twice the sum of the four medians, gave **20.695759 seconds** per session. All nine sessions used identical comparison-context hashes, candidate payloads, calibrated costs, resource configuration and oracle. Seed order was balanced across strategies.

| Seed | Strategy | Workers started | Completed in budget | Generic edges / 2 | Route obligations / 8 | Elapsed seconds |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 11 | random | 10 | 9 | 2 | 8 | 20.022 |
| 11 | dependency_greedy | 10 | 9 | 2 | 8 | 20.106 |
| 11 | route_greedy | 12 | 11 | 2 | 8 | 19.716 |
| 29 | dependency_greedy | 13 | 12 | 2 | 6 | 19.720 |
| 29 | route_greedy | 10 | 9 | 2 | 8 | 19.717 |
| 29 | random | 13 | 12 | 2 | 8 | 20.028 |
| 47 | route_greedy | 11 | 10 | 2 | 8 | 19.712 |
| 47 | random | 13 | 12 | 2 | 6 | 19.708 |
| 47 | dependency_greedy | 13 | 12 | 2 | 6 | 20.009 |

There were **105 started workers, 96 completed cases and nine interrupted final cases** across the sessions. Completion describes the harness; it includes application rejections and server errors. Each session stopped under the common deadline/one-second cleanup-reserve policy. No late or interrupted case earned feedback, and no deadline overrun was measured in this accepted batch. This observation is not an OS-level zero-overrun guarantee. All 131 resets across validation, calibration and sessions matched the run's fixture hash. All 131 parent cleanup records confirmed either process exit or that no browser launch had been attempted.

This pool has one workflow, two generic dependencies and eight route obligations. Route coverage partly measures the proposed selector's own objective. These nine engineering sessions cannot establish defect-detection advantage or generalization; no statistical superiority test is claimed. The paper's seven-template exploratory development batch remains a separate dataset, with unchanged counts and adjudication.

## Interruption and unsuccessful attempts

- `generated-integration-20261107T061521Z`: all 18 untimed validations completed, then the run was interrupted before calibration for review corrections. Its old raw summary retained `running`; a separate attempt-status record explains the interruption.
- `generated-integration-20261107T062607Z`: first live browser timeout/reset smoke check passed.
- `generated-integration-20261107T062638Z`: validation, calibration and six sessions completed; session seven stopped because parent process enumeration was unconfirmed. Application and worker checks had passed. The parent inspection ended after 0.255 seconds under a 0.25-second subprocess limit; the old helper did not record exception type. This incomplete attempt and its matching protocol remain preserved and are not pooled with the accepted batch.
- `generated-integration-20261107T063425Z`: revised live smoke passed. An active-browser case was interrupted after 3.055 seconds under a 3.5-second allowance, received no feedback, and was followed by a successful fresh-reset control.
- `generated-integration-20261107T063526Z`: complete accepted validation, calibration and nine-session batch.

The launcher records unique ownership before browser launch. The revised cleanup helper retains observed descendant identities across interrupted cleanup, verifies process identity before signalling, and uses bounded TERM/KILL phases. Only inspection timeouts may be retried within those phases; two fresh empty scans are still required. Other inspection errors fail closed. The research suite passes **75 tests**: 34 selector/registry unit tests, five source-pool consistency checks, 17 runtime-controller tests and 19 cleanup tests. Mocked escalation/recovery tests and the live interruption check provide different evidence; the live check did not need forced browser SIGKILL.

## Quartz and the next corpus

Quartz Manager 5.0.1 completed UI/UI, API/UI, UI/API and API/API stored-job creation, description edit and fresh read controls. The four routes share complete initial and final state hashes and the same native admin role. No triggers or job executions occurred; the scheduler remained stopped. This is one workflow and four executions. Classpath and JVM-timezone prerequisites are documented; upstream Quartz application unit suites were not run.

The prospective Quartz v2 pool contains **44 unexecuted cases**: four route controls, 16 accepted-value cases, eight normalization cases, ten rejection cases and six unresolved key-policy cases. Forty UI-producer mutation combinations have explicit exclusions. The existing generator code is unchanged. The original 14-case v1 pool remains a rejection/control stratum. Neither pool constitutes an executed held-out effectiveness result. V2 still needs a runtime adapter for its declared resource and state bindings, positive-control validation, and a dated primary protocol freeze.

The next empirical milestone is a multiworkflow paired-oracle corpus: compare competent API-semantic continuations with native UI continuations on matched accepted states, adjudicate distinct root causes, and preserve intentional differences and unresolved policies. Independent human adjudication is still pending. Broader selector-effectiveness evaluation follows only when the corpus has enough independent workflow/dependency structure.

## Evidence and reproduction

- [Accepted run](../results/generated-integration-20261107T063526Z/summary.json), [recomputed accounting](../results/generated-integration-20261107T063526Z/runtime-checks.json), and [post-run service checks](../results/generated-integration-20261107T063526Z/post-run-health.json).
- [Runtime protocol](../protocol/runtime-integration-v1.md), [next freeze gates](../protocol/multiworkflow-freeze-gates-v1.md), and [Quartz control record](../manifests/quartz-transfer-control.json).
- [Quartz v2 registration](../manifests/quartz-job-generation-v2.json), [generated pool](../manifests/quartz-job-generated-pool-v2.json), and [constraint/binding notes](quartz_registry_v2_constraints.txt).

Recompute the accepted accounting from this project directory after restoring its complete raw run directory. The source checkout includes compact summaries only; see `results/README.md`:

```sh
python3 scripts/summarize_runtime_integration.py results/generated-integration-20261107T063526Z
```

Use the RealWorld environment described in `notes/realworld_setup.txt`. `scripts/run_generated_integration.py` accepts the same `--subject`, `--python`, `--node` and `--runtime-root` paths as the positive-control runner. Set `PLAYWRIGHT_MODULE_PATH` to the installed Playwright package. Use `--phase deadline-smoke` for the separate interruption/reset check, or the default `all` phase for validation, fresh cost calibration and the nine-session schedule. Require ports 18765/18766 to be free. The runner preserves sources, protocol, pool, costs, fixture/build hashes, requests, observations and cleanup evidence. It does not reuse costs or completed sessions from an interrupted attempt.
