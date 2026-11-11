# Historical calibration result, 2026-11-11

The [registered calibration](../protocol/write-preservation-calibration-v1.md) completed in [run 43079843246](https://github.com/shravaniparsi/mixed-interface-study/actions/runs/43079843246), source cb01782ecad9e17a3db22641021e6428b90c509b. Both jobs passed. Independent reconstruction from raw SQLite rows passed every calibration gate. The first dispatch failed compilation before test execution; its artifacts and the single instrumentation correction remain retained separately.

| Observation | Historical version | Fixed version |
|---|---:|---:|
| Executions | 6 | 6 |
| Advertised schema accepts request | 6 | 6 |
| Operation reports success | 6 | 6 |
| Requested note edit persists | 6 | 6 |
| Unexpected original_order change | 4 | 0 |
| No-order control stays NULL | 2 | 2 |

Each version runs three cases through two channels. The imported-row edit and explicit empty-note edit change original_order from 0 to NULL on the historical code. The fixed code preserves 0. A row initialized without an order stays NULL on both versions. Every direct-command final row matches its MCP counterpart. No other unexpected column change occurs.

This is one reproduced, previously reported backend mechanism, not four bugs and not an MCP-only defect. The actual MCP dispatch reaches the same faulty command behavior as the direct path. Both schema validation and requested-edit postconditions pass despite the historical state loss. A competent full-row preservation check detects all four manifestations. That check is an existing baseline; this calibration establishes no new detector advantage.

State comes directly from SQLite, bypassing the application's defective getter. Production functions remain unchanged; only a test module was appended. The MCP SDK uses an in-memory transport, with real dispatch and persistence. No model, external Sheet operation, browser, production data, or remote service was involved. External spreadsheet ordering consequences remain an upstream report, not an observed outcome here.

The two application runs used four jobs and 6.05 elapsed job-minutes, including both failed compilation jobs. Paid model calls: zero. This is not a billing statement and excludes unit checks, earlier cohorts, local work and assistant/tool usage. See [accounting](../manifests/write-preservation-calibration-cost-v1.json).

## Contribution decision

Replay feasibility passes. Q1-readiness does not. The result supplies one verified historical benchmark seed and illustrates why blame must distinguish MCP adapters from shared backend behavior. The independent-input study's zero incremental detections remain unchanged; its denominator is not combined with this outcome-selected replay.

Adjacent work also limits broad method claims: [Differential Regression Testing for REST APIs](https://patricegodefroid.github.io/public_psfiles/issta2020.pdf) already compares API versions using shared inputs. [SATORI](https://arxiv.org/abs/2508.16318) describes static oracle inference from API specifications; its abstract was screened, not its entire evaluation. [RESTestBench](https://arxiv.org/abs/2604.25862) and [MCPEvol-Bench](https://arxiv.org/abs/2607.14642) are additional benchmark leads requiring full-text/artifact comparison. Do not claim automated semantic checking or MCP benchmarking is itself new.

Next steps, before a larger study:

1. Complete full-text/artifact comparison against these methods and benchmark corpora. Resolve the metadata/artifact anomalies in the earlier contribution-gate note rather than treating them as verified priority evidence.
2. Assess two contrasting historical mechanisms already exposed during screening: Iris incomplete read/merge and Superset presence loss during normalization. For Iris, read-only history screening now identifies fixing commit ebba6c1036e86cac407c2614e41c2039ac56c8f7 and parent a02a45480b8f801f5d5eab8c3da19d131cd3ed7c; these are leads, not executed evidence. A combined backend/adapter fix needs separate component ablations to attribute effects.
3. If multiple mechanisms are cheaply reproducible, specify the proposed method's incremental contribution over schema, requested-postcondition, full-row-frame, and existing presence-aware fixes. Include legitimate cascades and explicit resets as controls; preservation alone can wrongly block intended changes.
4. Only then freeze an independent repository/workflow cohort before reading its issue outcomes. Known-fix cases remain development data. Report all qualification failures and null results; do not search indefinitely for a target number of bugs.

No further calibration dispatch is pending. The next research question is whether a useful automated method or benchmark contribution survives these comparisons, not whether the known defect can be reproduced again.
