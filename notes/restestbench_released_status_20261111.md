# Released RESTestBench result-status audit

A complete exact-status screen of the pinned release found six entries where mutation application failed but the corresponding evaluation credited a killed mutant. All six are also present in the consolidated CSV scores. This establishes a scoring discrepancy in the released data, beyond the synthetic harness reproduction. It does not establish a change in published rankings or conclusions.

## Scope and provenance

The selection rule in `protocol/restestbench-released-status-audit-v1.md` was written before scanning result bodies, after inspecting directory listings and the scoring source. All execution and evaluation JSON files under the three released run directories were included. The combined recursive GitHub listing was truncated and was discarded as a coverage source. Three separate, untruncated subtree inventories supplied the complete selection: 360 execution files, 360 evaluation files and three consolidated CSVs. All 723 files match their pinned Git blob identifiers. The selected source files are retained in a compressed archive of about 5 MB; reconstruction requires no network or application execution.

There are 63,636 execution-result records, including 26,400 valid-context and 37,236 mutated-context records. These are correlated test records, not independent defects or confirmed successful application executions. The exact message `Mutation could not be applied` occurs six times. Each has return code -1, duration zero, a passing matching valid test and a killed-mutant entry in the paired evaluation. Joining by run directory, output folder and generation context finds all six in the consolidated CSV, with matching scores and killed-mutation counts.

| Model | Description | Released score | Unapplied mutation credited |
|---|---|---:|---:|
| Kimi | Vague | 15/22 | 1 |
| GPT-5 Mini | Precise | 22/22 | 1 |
| Kimi | Precise | 9/22 | 1 |
| Sonnet 4.5 | Precise | 22/22 | 1 |
| Mistral Mid | Vague | 12/22 | 1 |
| Sonnet 4.5 | Vague | 19/22 | 1 |

All matches are in `results_1`, TodoApp requirement 12, zero-based mutant index 1, valid-generation/zero-shot results. This is one mutation setup problem repeated across six evaluations, not six distinct defects. No exact-status matches occur in the other two released run groups. This screen does not certify other failure statuses or mutation applicability.

Removing the unsupported credit subtracts one numerator point from each listed score. Holding the original denominator of 22 fixed would lower each by 4.55 percentage points. That arithmetic is a sensitivity calculation, not a corrected benchmark estimate: excluding an unavailable mutant changes eligibility and potentially the denominator, and requires a consistent policy across tools. No new aggregate rankings are computed here.

The requirement ID sets in every released evaluation agree within each service: FastAPI 1–63, NestJS 1–29, TodoApp 1–14. This resolves the release-level cohort to 106 IDs, despite the README's 26 for NestJS. It does not independently establish which subset was used for every published figure or validate requirement semantics.

## Consequence for our study

The benchmark remains a candidate, not an admitted scientific test set. A future comparison needs explicit mutation-application status, valid-run qualification, separation of generator inputs from mutation labels, and golden-test validation. This finding strengthens the evaluation protocol; it does not demonstrate our proposed contract-inference method's incremental value or establish a Q1-level contribution by itself.

Run `python3 scripts/extension/audit_restestbench_released_status_v1.py --verify` to reconstruct the joins and source checks. The raw release is [RESTestBench at 4decc1e3](https://github.com/casablancahotelsoftware/RESTestBench/tree/4decc1e36ea3dd41b64ce3e3ac6a85bc72df36ae/results/runs). Upstream material retains the repository's AGPL-3.0 license, copied in `evidence/restestbench-source-v1/LICENSE`. No external issue, message, paid call or application experiment was performed.
