# Complete mutant runtime qualification

Run [43144135284](https://github.com/shravaniparsi/mixed-interface-study/actions/runs/43144135284) executed the frozen registration at study commit `7ff74f4c955f075e7bd0dbd5d196af620bf0b00c` against RESTestBench commit `4decc1e36ea3dd41b64ce3e3ac6a85bc72df36ae`. Every planned trial has a retained record. There were no retries or instrument corrections during this phase.

| Service | Fresh valid controls passed | Registered mutants | Execution-qualified assertion failures | Setup/readiness failures | Unattempted |
|---|---:|---:|---:|---:|---:|
| FastAPI | 63/63 | 141 | 141 | 0 | 0 |
| NestJS | 29/29 | 65 | 64 | 1 | 0 |
| TodoApp | 14/14 | 22 | 22 | 0 | 0 |
| Total | 106/106 | 228 | 227 | 1 | 0 |

The 334 recorded trials comprise 333 executed golden tests and one pre-test failure. No executed mutant survived its assigned golden test in this run. The verifier reconstructed source installation, container restart, health, database reset, matching original-source control, subprocess exit and raw JUnit. All 227 qualifying failures were assertion failures in the supplied golden tests. They are not 227 new application defects or measurements of our own generator's accuracy.

NestJS requirement 5 mutant 0 replaces the deletion return value with `{ affected: 1 }`. The retained application log reports TypeScript TS2741 because `DeleteResult` requires `raw`. Its original-source control passed, but the mutant never reached health and its golden test was not executed. It receives no detection credit in the qualified assertion count. This classification is specific to the recorded environment; the mutant was not repaired or silently dropped.

The three jobs used 39.3 application-job minutes against the registered 120-minute ceiling, with zero paid model calls. All applications ran on standard public GitHub runners. These minutes are measured execution time, not a monetary invoice.

## What the failures exercise

The post-hoc AST/source analysis maps each observed failing traceback site to the pinned golden test. It finds 109 HTTP-status assertions and 118 other assertions. Failure text explicitly shows a 5xx response in 25 cases (FastAPI 20, NestJS 4, TodoApp 1). These are first-failure observations, not a counterfactual replay of a status-only baseline. They do not establish that other assertions or later requests would pass.

Grouping static installations by service, target path, and before/after bytes gives 221 distinct source changes across 228 requirement-mutant trials: FastAPI 136, NestJS 63, TodoApp 22. One distinct NestJS change is unready, leaving 220 distinct executable changes in this run. Distinct bytes do not establish independent semantic defects. The registered 228-trial denominator is retained; grouping does not alter results.

## Historical follow-up and its limits

An outcome-informed follow-up examined all 120 released NestJS execution files for the same requirement-5 mutant under valid-generation tests. It found 39 recorded mutant executions, all with passing original controls and evaluator credit. Of these, 17 released outputs explicitly contain `ConnectionResetError` and 16 contain `RemoteDisconnected`. Six lack an explicit exception marker in the retained fragment. All 39 outputs are exactly 2,000 characters, the cap implemented by the pinned executor's serializer.

These records show credited failures with connectivity symptoms. They do not establish that the historical cause was the TypeScript error observed now, or that every credit is invalid under the original benchmark's scoring objective. No additional confirmed unsupported credits are added to the six failed-installation credits previously established. Analysis v1 retained only the initial marker inventory; v2 adds remote disconnects and the output-cap analysis while preserving v1.

## Research decision

Qualification is complete. The executable subset is usable for a declared requirement-conformance comparison, subject to exposed labels, correlated mutations, and the oracle-scope limitation documented separately. We have not run a new generator, demonstrated automatic contract inference, or established superiority over direct natural-language test generation or complete manual contracts. More repetitions of these golden tests would not close that contribution gap.

The earlier checker ablation still shows zero incremental alerting records from agreement checks over complete manually supplied transition contracts. The six confirmed historical scoring credits have limited bounded ranking impact: two pairwise strict comparisons can become ties, with no strict reversal under that analysis. These results do not support a Q1-readiness claim. The next scientific gate is a concrete additional capability and a fair registered comparison, not more infrastructure qualification or a stronger manuscript claim.

## Reconstruction

- `python3 scripts/extension/verify_restestbench_mutant_runtime_v1.py --archive results/restestbench-mutant-runtime-v1-ci-43144135284 --output manifests/restestbench-mutant-runtime-results-v1.json --verify`
- `python3 scripts/extension/build_restestbench_mutant_identity_v1.py --verify`
- `python3 scripts/extension/build_restestbench_assertion_analysis_v1.py --verify`
- `python3 scripts/extension/audit_restestbench_nestjs_unready_v1.py --verify`
- `python3 scripts/extension/audit_restestbench_nestjs_unready_v2.py --verify`

The raw archive, source bundle, run/job metadata, per-trial proof, post-hoc classifications and original failure are retained. Golden source files in the assertion-analysis bundle match the previously pinned source hashes and remain covered by the retained upstream AGPL license at `evidence/restestbench-source-v1/LICENSE`.
