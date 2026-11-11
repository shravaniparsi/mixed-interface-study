# How much of the replay result depends on manual contracts?

This post-hoc analysis changes only the information supplied to the checker. It uses the existing 44 historical records from three projects, with no new application execution. All modes receive the same manually mapped requested assignments. The full manual contract is a comparison reference, not independent ground truth.

| Checker information | Tiller alerts / 12 | Iris alerts / 24 | Fast Dash alerts / 8 |
|---|---:|---:|---:|
| Requested assignments only | 0 | 0 | 0 |
| Preserve every other field | 4 | 24 | 1 |
| Preserve other fields, permitting documented derived changes | 4 | 1 | 0 |
| Also check expected values of derived changes | 4 | 1 | 2 |
| Also check state/readback/invocation-argument agreement | 4 | 1 | 2 |

The unqualified preservation rule flags all 24 Iris records, including 23 not flagged by the full contract, because it also objects to the permitted timestamp change. Adding derived-field exceptions removes those disagreements but misses both Fast Dash parent-change failures: allowing the child to change does not specify what its new value must be. Checking the declared derived value recovers both observations.

Agreement checks add **zero additional alerting records over the complete transition contract** in this corpus. They provide evidence about the fixed Fast Dash discrepancy, but cannot be presented here as an incremental detector. The reference's seven alerting records remain manifestations in three projects, not seven independent defects. Relative disagreements are not precision, recall or estimated population error rates.

This result identifies the actual information gap. It is insufficient to infer only a set of fields allowed to change; an automatic method must also recover the expected conditional effects, distinguish absence from explicit null, and justify exceptions without copying the faulty implementation's behavior. Conversely, a complete manual transition contract is already a strong baseline. A comparison only against schema checks or unqualified preservation would be inadequate.

The new [prior-art verification](contract_inference_prior_art_20261111.md) further rules out before/after contract checking as a novelty claim. Our result is a diagnosis of baseline information requirements, not proof that the remaining inference problem is novel or solved. The shared replay remains useful development infrastructure; the Q1 contribution gate remains unmet.

Reconstruction: `python3 scripts/extension/build_contract_information_ablation_v1.py --verify`. The manifest retains all record-level decisions, project-level disagreements, source hashes and implementation hash. The closed application cohort and its exclusions are unchanged.
