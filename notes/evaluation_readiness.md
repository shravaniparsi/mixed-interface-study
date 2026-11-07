# Evaluation preparation

Update: source-qualified RealWorld/PetClinic extraction is implemented, qualifying 140 of 144 archived records and retaining four RealWorld capture-error records as incomplete. A Quartz controls-only paired wrapper is implemented. See [the extraction report](oracle_extraction.md) for the current evidence; the original preparation checkpoint below remains historical.

The eligibility ledger now accounts for all eight existing workflow templates across three applications. All eight are retained. Their versions, actors, reset procedures, operation bundles, returned-resource bindings, preservation rules, constraint variants, source conflicts and exclusions are recorded in [the detailed ledger](../manifests/multiworkflow-eligibility-v1.json). Retention means that a workflow remains in the research inventory; execution readiness is recorded separately.

| Application | Workflow | Main work still needed before primary paired execution |
| --- | --- | --- |
| RealWorld | Article create → body edit | Separate shared UI checks from API observations; explicit rejected-prefix state check; consistent tag normalization |
| RealWorld | Article update → comment create | Source-qualified component extraction; exact request and returned comment/parent binding checks |
| RealWorld | Comment create → delete | Component extraction; verify the native deletion target and common permission scope |
| RealWorld | Profile update → settings edit | Component extraction; loaded-field and actual-request guards; fixed null-omission rules |
| PetClinic | Owner create → address edit | Separate shared probes and harness errors; rejected-prefix side-effect checks; bounded cleanup |
| PetClinic | Pet create → rename | The owner-workflow infrastructure gaps, plus explicit loaded date/owner and returned-relationship checks |
| PetClinic | Visit create → reschedule | The owner-workflow infrastructure gaps, plus consistent returned pet/owner binding |
| Quartz | Stored-job create → description edit | Pair-level state validation, campaign order/repeats and effective runtime configuration; component extraction is implemented |

## Registered pair inventory

The [pair index](../manifests/paired-candidate-inventory-v1.json) contains 73 declared pair entries, separated into:

- 42 previously examined development pairs: 24 RealWorld and 18 PetClinic. Two additional RealWorld UI-only controls remain outside the paired denominator.
- Nine generated RealWorld engineering pairs. They overlap the development workload and do not add independent samples.
- 22 Quartz pairs: two previously executed route-control pairs and 20 source-inspected mutation pairs. All 40 Quartz mutation branches remain unexecuted.

The index pairs generated candidates only when their producer, intended consumer input, mutation and expectation scope agree, changing only the continuation interface. It rejects missing counterparts and duplicate IDs. Legacy pairs retain their original registry declarations. This verifies declared pairing, not the equivalence of the implemented operations or observed prefix states.

## Measurement correction

Some existing runners finish either continuation with shared verification. For example, Quartz's `fresh_native_final_read` and RealWorld's `shared_ui_read`/`shared_ui_render` also run after API continuations. Their aggregate case status cannot be used as the API oracle's result. Likewise, a direct API readback after a UI action must retain its readback origin and action context; it is not automatically a native-only observation.

The new Quartz component reducer reads existing evidence and separates immediate responses, prefix-state inspection, assigned actions, shared API readback, supplementary UI reads, execution integrity and unresolved policy. Its vocabulary is tied to the exact executed adapter and registry hashes. Missing, unknown or incomplete evidence cannot become a clean result. The hosted four-control artifact is the validation input; no new application or boundary run is required to test this extraction. The reducer does not assign defects, deduplicate root causes or compute paired detection overlap.

The [analysis specification](../protocol/paired-oracle-analysis-v1.md) defines component attribution, pair-validity conditions, separate denominators, repeat/control rules and descriptive reporting. The old raw records and failed attempts remain unchanged.

Validation passed 106 Python harness tests, six CI bootstrap/context tests and eight Node adapter tests, 120 in total. The new coverage includes ten pair/provenance checks and 21 Quartz component checks. Read-only reduction of the saved hosted Quartz controls produced four complete observations with no evidence issues. [Validation record](../results/evaluation-preparation-20261107/validation.json) · [Component observations](../results/evaluation-preparation-20261107/quartz-component-controls.json).

## Freeze status and next implementation

The [dated preparation snapshot](../manifests/evaluation-preparation-v1.json) hashes the corpus, ledger, protocol, analysis code, adapters and relevant CI configuration. CI verifies the required artifact set and exact contents. A removed hash entry, changed source file or altered pair inventory fails verification. This is a preparation snapshot; **the primary evaluation freeze is not complete**.

Next, repair future RealWorld capture shutdown, add the executing adapters’ missing payload/binding and rejection-state guards, and validate/extend the independently reset paired campaign on ordinary controls. Freeze effective commands, environment, ordering and repeat behavior before running unexecuted boundaries. Timed selector evaluation additionally needs the common multiworkflow runtime and cost/deadline validation; that is a later gate.

Disputed policy and root-cause adjudication remain separate from these engineering tasks. Unknown policy can remain an explicit result category. Human agreement or maintainer confirmation will not be claimed from agent review.
