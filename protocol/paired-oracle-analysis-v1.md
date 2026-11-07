# Paired-oracle evaluation specification v1

Status: prospective preparation specification. The eight-workflow ledger and its dated preparation snapshot record remaining execution gaps. This document does not mark the primary evaluation frozen or authorize new boundary execution.

## Question and inventory

The first comparison asks what native UI continuation observes beyond the corresponding API-semantic read/action/readback after the same producer operation. Immediate response checks are a separate baseline. Interface disagreement is an observation; a defect label requires an applicable requirement and adjudication.

The inventory accounts for eight workflow templates in three applications. The existing catalogs contribute 42 declared paired development candidates and two UI-only control candidates, nine generated RealWorld engineering pairs, and 22 Quartz pairs. Quartz comprises two previously executed route-control pairs and 20 source-inspected mutation pairs whose 40 branches have not executed. Some RealWorld catalog entries overlap across development and engineering. These counts are catalog entries, not independent samples; neither pools nor reruns are added together as evidence of sample size. Previously observed cases remain development or engineering evidence.

`manifests/paired-candidate-inventory-v1.json` preserves source case IDs and source-registry hashes. For generated candidates, pairing requires identical producer interface/input, intended consumer operation/input, transformation and declared expectation, changing only the consumer interface. Legacy registries declare the pair directly. These checks establish intended pairing; each workflow's actual binding, payload and preservation parity must also pass its ledger gates.

## Observation components

Every check must be assigned by an explicit, source-version-qualified mapping. An aggregate case status, HTTP status alone, or trace timestamp cannot supply this attribution. Asynchronous network callbacks can be recorded after the operation that issued them.

| Component | Permitted observations | Interpretation |
| --- | --- | --- |
| Immediate producer response | Status, declared response shape, fields and returned reference directly available in that response | Immediate baseline; no later reads included |
| Prefix-state inspection | Persisted producer state and rollback checks before continuation | Additional diagnostic evidence, separately costed; not immediate-response detection |
| Assigned continuation | Resource read, meaningful edit or transition, actual request and corresponding persisted readback | API-semantic or native UI channel according to the assigned continuation |
| Shared verification | Extra final native UI read/render, relationship or inventory probes not contained in the declared channel contract | Shared diagnostic evidence; cannot create API-only or UI-only credit |
| Execution integrity | Actor, reset, actual-input consistency, resource ownership, cleanup, unavailable service, harness error | Determines whether the observation is interpretable; not an application defect by itself |
| Unresolved policy | A check for which the required behavior is unresolved | Retained without a normative violation label |

Readback needs an explicit contract per workflow. An API read used as the common persistence measurement for both continuations must be reported symmetrically; an extra shared graph probe cannot be credited exclusively to the UI channel. A native UI operation may legitimately issue network requests; those requests do not make it an API-only continuation. Actual-payload mismatches also require attribution: an adapter that fills the wrong declared input is an execution error, while a native form that changes a correctly loaded, unedited value is an application discrepancy to adjudicate.

The generated RealWorld adapter performs `shared_ui_read` and `shared_ui_render` after either continuation. Its `one_article` check follows those probes and may be unobserved after a UI failure. The Quartz adapter similarly performs `fresh_native_final_read` after both continuation routes. Their aggregate outcome must not be reused as an API-semantic outcome. The new Quartz reducer partitions the recorded evidence without rewriting it; the remaining adapters still need equivalent reviewed mappings and completion/error handling.

Per component, report violation observed, no violation observed, not reached, incomplete, or unresolved policy as supported by its required evidence. Missing checks, timeouts and unknown check identifiers cannot become clean passes. A policy-unresolved case can still contain an unrelated, separately attributable requirement discrepancy. None of these component signals is automatically a confirmed defect or a distinct root cause.

## Pair execution and validity

Each continuation begins from an independently restored equivalent starting state and an independently replayed identical prefix. Never run the two continuations sequentially on one evolving resource. Bind resource identities and preserved fields from the accepted producer response/state under the registered contract; do not repair a suspect field from the valid baseline. Match actor, lifecycle, intended operation and fresh-session semantics. Preserve all failed attempts.

Before admitting a pair, verify recorded starting-state equivalence, exact prefix inputs, accepted producer identity and declared post-prefix business-state equivalence. Generated timestamps and other excluded runtime fields need explicit normalization rules, not ad hoc equality exemptions. If one prefix is rejected, or replayed states disagree, the pair does not yield a clean continuation contrast. Record the two observations and classify pair validity separately. Rejected prefixes stop before continuation and receive no downstream coverage; their post-request state still needs a rollback/state check.

The proposed first execution order is deterministic registry order within application/workflow, alternating API→UI and UI→API continuation order between consecutive paired candidates. Each branch still resets independently. UI-only controls remain controls. The campaign runner must implement and archive this schedule before the final freeze; the current separate legacy runners do not establish that it has been implemented.

After the first complete paired sweep, repeat every candidate with a channel discrepancy, requirement-check failure or unresolved execution outcome twice more from fresh resets. Repeat the workflow's registered ordinary valid control twice per continuation alongside it. Use that predeclared reference control, not a post hoc successful payload; additional minimized variants are separately registered diagnostics. Retain all three candidate attempts and all controls. If the repeated prefix or channel outcome differs, report variability and unresolved attribution rather than choosing a preferred attempt. Repeated observations do not add independent root causes.

## Adjudication and reporting

Keep observation extraction separate from requirement-based adjudication. Each candidate packet should contain the requirement source and its authority, source conflicts, exact input, actor/state evidence, component signals, repeats and controls. A UI restriction, API acceptance or implementation-source prediction is insufficient alone to establish a defect. Keep known issues, previously examined findings, historical buggy/fixed pairs, injected faults and unknown-prior-report-status findings separate. Do not call an unknown-prior-status finding new without an appropriate issue search.

For interpretable paired observations, report API-only, UI-only, both, neither and unresolved signals by workflow. Separately report the same overlap for adjudicated root causes, linking all affected pairs to the deduplicated cause. No confirmed-root-cause table is populated before adjudication. Unresolved policy is a retained outcome, not grounds for silently deleting a candidate. Human review may settle disputed requirement judgments; AI review cannot supply human agreement statistics.

Denominators must distinguish registered candidates, eligible pairs, attempted branches, accepted prefixes, reached continuations, completed components, blocked UI submissions, timeouts and harness failures. Report conditional continuation outcomes alongside the full attempted denominator. With three applications and reused development data, the default analysis is descriptive by application and workflow. No prevalence claim, population significance test or selector-effectiveness conclusion is planned from this preparation inventory.

Record setup, reset, authentication, producer, continuation, shared verification, evidence capture and teardown costs. A pure component cost cannot be recovered from a phase that combines shared UI work with API readback; add instrumentation before claiming such a cost. Equal-candidate diagnostic overlap does not establish practical efficiency. The later selector comparison retains its separate common-budget protocol and requires a richer, validated multiworkflow execution pool.

## Conditions for the final freeze

Close the concrete ledger blockers for every included primary workflow, or register a justified scope amendment before examining new outcomes. Pin the final corpus, adapters, attribution rules, requirements, preservation/normalization rules, pair schedule, repeat policy, timeouts and cost instrumentation. Record resolved environment versions and hashes; moving CI labels are not a final environment freeze. Validate clean controls and interruption cleanup followed by a fresh reset on the selected execution environment. Retain the failed validation attempts.

The final dated record must link those artifacts and unresolved adjudication items and explicitly identify the scope it freezes. The preparation snapshot deliberately records `primary_freeze_complete: false`. Missing executable capabilities must be fixed rather than hidden behind a signed-off plan.
