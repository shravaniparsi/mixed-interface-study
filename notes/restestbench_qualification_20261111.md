# RESTestBench admission check

The candidate benchmark is pinned to [4decc1e36ea3dd41b64ce3e3ac6a85bc72df36ae](https://github.com/casablancahotelsoftware/RESTestBench/tree/4decc1e36ea3dd41b64ce3e3ac6a85bc72df36ae). It is independently authored, but publicly available and already exposed through its paper and README. It is not automatically an uncontaminated held-out dataset. No scientific test-generation evaluation is registered or dispatched by this check.

## Inventory and information boundaries

The pinned directory listings contain 63 FastAPI, 29 NestJS and 14 TodoApp requirement JSON files: 106 files. The README lists 26 NestJS requirements. File bodies have not been parsed in this pass, and the exact paper-selected subset has not been established; do not substitute either count for a scientific denominator. Per-file Git blob identifiers and sizes are preserved.

The generator's call to the tool passes scenario text, specification path, output/reset paths and service URL; it does not directly pass the mutant object as an argument. The raw requirement representation contains mutation code, and the plugin runs in the same checkout. Therefore the interface alone does not establish isolation from labels or golden tests. This inspection found no evidence that the authors' tools read those labels improperly. A future evaluation needs a physically separated generator-input bundle and an explicit exposure record.

## Reproduced scoring failure path

In the pinned executor, a failed `apply_mutation` produces an execution-result entry with `passed=False`, return code -1 and the message `Mutation could not be applied`. It skips running the test against that mutation. The evaluator counts any failed mutant result as killed, provided the valid run passed. It does not distinguish this setup failure in that scoring path.

A local qualification probe imported the unmodified upstream Mutator, TestExecutor and Evaluator. A disclosed synthetic lifecycle fixture reset a temporary Python value file; it did not launch a REST service. Tests ran as actual subprocesses. Git blob hashes confirm source identity, and the upstream license is retained.

| Probe | Mutation applied | Actual test processes | Upstream kill score |
|---|---|---:|---:|
| Change value, test detects it | Yes | 2 | 1 |
| Mutation search string absent | No | 1, valid fixture only | 1 |
| Equivalent comment change | Yes | 2 | 0 |
| Test already fails on valid fixture | Not attempted | 1 | 0 |

The second row verifies kill credit without a mutant test execution. It does not establish that published results contain such entries, how often the path occurs, or whether any reported model ranking changes. Novelty or previously unreported status has not been checked. This is benchmark-harness evidence, not a natural REST/MCP defect added to our scientific cohorts.

## Admission decision and next checks

Do not use the aggregate kill score unqualified. Before scientific admission, inspect the available raw result records for this failure status; distinguish an applied mutation with an executed failing test from failed setup, timeout and unrelated execution errors. Preserve the original score and any corrected classification separately. A tool timeout cannot automatically be declared infrastructure failure either: its cause must be investigated.

Also reconcile the selected requirement set, separate generator inputs from labels, and validate golden tests on both valid and applied-mutant services under a bounded protocol. These are prerequisites to using this benchmark, not evidence that a proposed inference method is new. No third-party issue or message has been posted.

The probe ran locally with Python 3.12 and the existing Requests installation available via PYTHONPATH; it made no network request or paid model call. No package installation, Docker run or GitHub application job was needed. The local environment versions and complete observations are archived in `results/restestbench-scoring-probe-v1/observations.json`.

Reconstruct with `python3 scripts/extension/verify_restestbench_scoring_probe_v1.py --verify`. Upstream source: [executor](https://github.com/casablancahotelsoftware/RESTestBench/blob/4decc1e36ea3dd41b64ce3e3ac6a85bc72df36ae/src/executor.py), [evaluator](https://github.com/casablancahotelsoftware/RESTestBench/blob/4decc1e36ea3dd41b64ce3e3ac6a85bc72df36ae/src/evaluator.py), [generator](https://github.com/casablancahotelsoftware/RESTestBench/blob/4decc1e36ea3dd41b64ce3e3ac6a85bc72df36ae/src/generator.py).

Follow-up: the [released-result audit](restestbench_released_status_20261111.md) subsequently established six matching credits in released evaluation files and consolidated CSVs. The synthetic-probe manifest retains its original, narrower scope.
