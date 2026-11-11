# Write-preservation contribution gate, 2026-11-11

## Current decision

The completed independent-input study has 44 scientific paired executions, zero incremental native-only detections and zero confirmed natural defects. Its final unit run [43077280584](https://github.com/shravaniparsi/mixed-interface-study/actions/runs/43077280584) passed. These results do not establish Q1 readiness. They remain unchanged and separate from the work below.

A generic MCP schema-quality or omission/null-preservation contribution is not defensible as new. Proceed only to a bounded historical replay calibration, then reassess whether a benchmark or automated state-effect method would add value beyond existing techniques. No claim of novelty or Q1 acceptance is made.

## Primary-source checks

The claim-source-verification skill was applied with a fresh-context skeptic. Three proposed paper/source pairings were checked: 0 wholly confirmed, 3 PARTIAL, 0 wholly rejected. The substantive scope distinctions below are supported, but unresolved metadata/artifact issues prevent using them as unqualified bibliography or priority evidence.

| Primary source | Supported narrow statement | Unresolved issue |
|---|---|---|
| [Post-Wire Semantic Changes, II-A/B](https://arxiv.org/html/2610.00182v1) | Studies fixed tool results through framework carriers. Its unit ends before remote-provider processing. This is a scope distinction, not evidence that application-write research is new. | Identifier 2610 conflicts with September 17 v1 date shown on the abstract/HTML. Linked Zenodo artifact was not accessible to the verification tool. |
| [MCPGuard, V-B / Fig. 3b](https://arxiv.org/html/2611.03662v1) | Already describes defaults hiding wire-level omission during SDK parsing. The broad absence/default-collapse novelty claim fails. | Identifier 2611 conflicts with August 12 v1 date. No priority date has been inferred to reconcile the mismatch. |
| [Runtime Fault Taxonomy, Data Availability and §7](https://arxiv.org/html/2606.05339v2) | Links mined issues and coding data; explicitly limits prevalence claims to the studied corpus. | [Linked Figshare package](https://figshare.com/s/c1e1e802e1b9f38fddf0) is marked privately shared, advertises 1.59 GB, and describes 837 rather than the paper's 833 threads. Contents/version match unverified. Not downloaded given storage constraints. |

Supporting excerpts (each below 25 words per source):

- Post-Wire: “our unit begins with an already-produced result and ends before remote-provider processing.”
- MCPGuard: “A default makes a required wire field optional and hides the omission in the parsed object.”
- Taxonomy: “should be treated as descriptive evidence of the studied corpus, not as prevalence estimates across the MCP ecosystem.”

Also screened the abstracts of [REST-to-MCP generation](https://arxiv.org/abs/2507.16044) and [Description-Code Inconsistency](https://arxiv.org/abs/2606.04769). Their topics overlap generic wrapping and inconsistency claims. Abstract screening alone does not establish the exact remaining research gap. Do not import their numerical claims without full verification.

## Implementation evidence and rejected shortcuts

All listed cases were discovered by issue/patch-oriented searches after the independent-input study. Selection is outcome-biased. They cannot estimate prevalence or serve as an unseen evaluation cohort. Public reports, including AI-assisted reports, are leads until independently reproduced. No external issue or comment was posted.

| Record | What was inspected | Current interpretation |
|---|---|---|
| [atomic-agents PR 303](https://github.com/Eigenwise/atomic-agents/pull/303) | PR description and pinned head/base metadata | Existing proposed null/presence repair with nested-schema tests. Not merged at retrieval; not independently run. Generic preservation intervention is already implemented by others. |
| [CrewAI PR 8763](https://github.com/crewAIInc/crewAI/pull/8763) | PR description and head/base | Proposes dropping omitted None while retaining real defaults. Shows that blanket exclude_unset is not always equivalent to the intended tool contract. Not merged at retrieval. |
| [Browser Use PR 6291](https://github.com/browser-use/browser-use/pull/6291) | PR description and head/base | Another proposed presence/null-aware client. Not merged or independently reproduced here. |
| [CML v0.27.0](https://github.com/xorrkaz/cml-mcp/releases/tag/v0.27.0) | Release note, complete version comparison, LabRequest schema | Release note describes excluding unset write fields. In the inspected comparison, the relevant serialization change is an import operation; modify_cml_lab still excludes defaults/None. Reject the inference that the release proves a reproduced partial-update defect/fix. CML backend not run. |
| [LiteLLM PR 29253](https://github.com/BerriAI/litellm/pull/29253) | PR description | Reported management-endpoint partial-update bug. This configures MCP infrastructure; it is not a tool-to-application wrapper case. Exclude from a primary application-write corpus unless the scope is explicitly widened. |
| [Superset PR 44188](https://github.com/apache/superset/pull/44188) | Merged PR metadata and actual file diffs | Implements presence-aware normalization and preservation of two chart controls, with explicit-default/null and visualization-change tests. Potential historical replay case; simple exclude_unset and frame checks are competent baselines. Not our discovery. |
| [Vikunja issue 4109 / PR 4166](https://github.com/go-vikunja/vikunja/pull/4166) | Report, timeline, merged patch description | Explicit bulk field mask reportedly fails to protect associations/reminders/favorite state. Shared API/backend mechanism, reachable through MCP; not automatically MCP-specific. Previously exposed app. |
| [Iris issue 314](https://github.com/cgbarlow/iris/issues/314) | Issue report and closure timeline | Reported incomplete read/merge before full replacement, with a mocked response masking state loss. No immutable fix identified yet; not confirmed by us. |
| [tiller-sync issue 40 / PR 45](https://github.com/webern/tiller-sync/pull/45) | Report, merged PR, actual fixing commit and parent, MCP dispatch, fixture and schema sources | Selected single calibration mechanism. Actual fix is 3566bd3, parent dea54f9; PR head 6d1e808 is a merge, so using its first parent as an unfixed baseline would be wrong. |

Selected GitHub API snapshots and the complete CML comparison are retained under `evidence/write-preservation-gate-v1/`. Full third-party paper text is not bundled. The search is exploratory and non-exhaustive; neither result counts nor search ranking are used as denominators.

## What would constitute an advance

Historical replay can establish an inexpensive real-code benchmark pipeline and causal localization. It cannot establish an unseen detection advantage. The next method would need to handle documented write sets, explicit resets, legitimate cascades and derived changes, and outperform competent schema, postcondition and state-frame baselines on a separately frozen cohort. A mere count of known bug reproductions is insufficient.

The registered calibration is [write-preservation-calibration-v1](../protocol/write-preservation-calibration-v1.md). Its twelve executions cover one known defect and controls, across historical/fixed code and direct/MCP paths. Results remain pending until raw artifacts are reconstructed. This is a feasibility investment, not a replacement positive result for the completed negative study.
