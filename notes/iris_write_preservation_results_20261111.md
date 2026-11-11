# Iris component calibration result, 2026-11-11

[Run 43082290147](https://github.com/shravaniparsi/mixed-interface-study/actions/runs/43082290147) completed all five jobs successfully on study commit 8d303bd8b982d44c3f395766102cb34feb63e177. All 24 registered executions were observed; no correction dispatch was needed. The independent verifier reconstructs input validity, success, requested edits, row changes, outgoing payloads, membership queries and component provenance from raw artifacts.

## Component effects

The same grouped-set description edit produced the following outcomes through the actual MCP dispatcher:

| Backend | Adapter | Outgoing PUT carries collection_id | Membership after edit |
|---|---|---|---|
| Historical | Historical | No | Lost |
| Historical | Fixed | Yes | Preserved |
| Fixed | Historical | No | Preserved |
| Fixed | Fixed | Yes | Preserved |

All direct complete-field API controls preserved membership. Each experimental cell contains six executions: grouped and ungrouped description edits and an explicit collection clear, each through the dispatcher and direct API. Hybrid cells are constructed interventions, not released application versions.

The historical adapter omits a value that the old full-replacement backend needs to preserve membership. The adapter change carries that value forward; the backend change preserves it when omitted. Either intervention suffices in this case. The direct control deliberately sends a complete update, so its success is not evidence that an ordinary minimal PUT would also succeed. Nor does the result imply that every full-replacement backend behavior is a defect: the preservation obligation comes from the wrapper's partial-edit contract.

All 24 requests passed their respective advertised schemas, reported success, and persisted the requested change. One unintended collection_id change occurred, in the historical/historical grouped MCP edit. The fresh membership query then excluded the set from its original collection. No other unexpected set-row column change occurred; updated_at was prospectively allowed as a derived change.

All eight intentional-clear executions succeeded. An unconditional membership-preservation rule would raise eight false alarms on those designed controls. The intent-aware frame check raised none on them and detected the one unintended loss. It is a competent baseline, not a new algorithm, and these controls do not estimate a population false-positive rate.

## Evidence and scope

Each execution used fresh API-created resources, real authentication, FastAPI routes and SQLite. The public MCP tool dispatcher and IrisClient ran unchanged from the selected source. ASGI transport was in-process; no browser or MCP session/wire path was tested. The synthetic actor was an administrator. Raw row snapshots, business HTTP payloads, API readbacks and membership lists are retained without authentication headers or login payloads.

The four component files in every cell match the Git blob identifiers of the pinned historical/fixing commits. All cells installed exactly the same third-party package list frozen by the environment job before application execution. Source imports were asserted to come from the composed checkout. Cross-reset comparisons normalize only declared fixture identifiers and timestamps; within-execution frame checks preserve all raw values.

[Scientific reconstruction](../manifests/iris-write-preservation-results-v1.json) · [Protocol](../protocol/iris-write-preservation-calibration-v1.md) · [Component Git blobs](../manifests/iris-component-git-blobs-v1.json) · [Job accounting](../manifests/iris-write-preservation-cost-v1.json)

The run consumed 2.6 elapsed job-minutes across the dependency job and four execution jobs. Paid model calls: zero. This excludes unit checks, other cohorts, assistant/tool usage and local work; it is not a cash invoice or billed-minute total.

## Contribution gate

This is one previously reported mechanism, selected after its issue and patch were read. Together with Tiller, the project now has two independently reconstructed historical mechanisms: shared backend state loss, and a partial-edit adapter/full-replacement backend interaction. There are 12 Tiller executions and 24 Iris executions, not 36 independent defects. Neither calibration belongs to the completed independent-input cohort.

The result strengthens causal localization and benchmark feasibility. It does not establish a Q1-level contribution or incremental detector efficacy: a manually specified preservation frame detects both cases. More repeats would not address that gap.

The next decision must concern contribution and independent evaluation, not another replication of these mechanisms. A viable continuation needs an explicit advantage over competent frame/presence baselines, or a sufficiently distinct and useful benchmark contribution. Any new evaluation cohort must be frozen before its outcomes are read. Further known-fix cases are development data only. Superset remains an inspected but unexecuted historical lead; no scientific result is claimed for it.
