# Fast Dash cascade observations and incomplete repair

Run [43088065630](https://github.com/shravaniparsi/mixed-interface-study/actions/runs/43088065630) completed eight registered executions on study commit ab35803c006791650134b2a0f919557b68b6f2ab. All three jobs succeeded on the first attempt; no application rerun or instrument correction occurred. The six control executions qualified. The repaired parent-change case failed the predeclared state/readback agreement requirement, so the anticipated complete repair pattern was not established.

## Main observation

| Parent-change case | Independent state object | describe_app child value | Subsequent callback output |
|---|---|---|---|
| Historical parent | state = Karnataka | Karnataka | original: Karnataka, USA |
| Pinned repair | state key absent | None | original: <fast_dash.utils.depends_on object at …>, USA |
| Explicit-clear control, both versions | state = None | None | original: None, India |
| Already-clear then parent change, both versions | state = None | None | original: None, USA |

The historical case reproduces the reported invalid country/state combination. The pinned repair clears the advertised value but deletes its underlying key. Its subsequent invoke omits the child keyword argument, recorded independently in get_invocation.kwargs_summary. Python therefore supplies the callback's depends_on signature default. This differs from explicitly storing None, which the controls pass correctly. Raw output retains the real object address; the table shortens it for readability.

The archived fixed source supports this chain: `_clear_stale_dependents` removes keys with `state.inputs.pop`; invoke constructs kwargs only from keys present in the snapshot, then calls `fd.callback_fn(**kwargs)`. These are inspected production paths, not a newly executed code intervention. The fixing commit also changes unrelated behavior, so this is not a component-isolation experiment.

All eight operations pass the captured set_input schema, report success, and satisfy the explicitly requested field assignment. A manually specified contract check, including dependent clear, identifies the two parent-change state mismatches. A naive rule preserving all unnamed fields flags only the repaired deletion, while missing the stale historical value. The historical options-membership check detects the invalid child; the repaired advertised None passes membership, despite its divergent invocation. These observations motivate checking consumer behavior in addition to advertised state, but do not establish a new method's advantage over a complete semantic contract.

## Reconstruction and qualification

The first reconstruction script stopped when fixed-case readback equality failed. It is retained as v1. Reconstruction v2 records missing keys and value mismatches separately, keeps absence distinct from None, and returns `all_state_readbacks_qualified: false` and `predicted_repair_pattern_reproduced: false`. It does not convert the missing key into a valid clear or relax the original qualification rule. No result file from a purportedly successful v1 reconstruction exists.

Source blobs, archived observation hashes and shared dependency lock are verified. Both version jobs installed identical packages; captured pip freezes match the environment lock. Direct object snapshots match readbacks on all controls and the historical case. The new-client readback in the repaired parent-change case still advertises None, while invocation history omits the child. This is cross-request process memory, not database persistence, restart durability or browser execution.

[Reconstruction](../manifests/fastdash-cascade-results-v2.json) · [Frozen protocol](../protocol/fastdash-cascade-calibration-v1.md) · [Accounting](../manifests/fastdash-cascade-cost-v1.json)

The run used 1.9833 elapsed job-minutes, including environment resolution, and zero paid model calls. The bounded expansion has now used 6.5833 elapsed application-job minutes including both Vikunja attempts. These are elapsed runner times, not cash invoices, and exclude unit checks and assistant/tool usage.

## Contribution and remaining work

The study still has two fully qualified historical repair calibrations (Tiller and Iris), plus this eight-execution cascade investigation with one reproduced reported symptom and an unanticipated repair discrepancy. Do not count the two parent-change outcomes as independent discovered defects, or call the repair discrepancy previously unreported. Three targeted issue searches surfaced related Fast Dash reports, but have not established its novelty or current-release status. No issue or message was sent externally.

This is stronger evidence about the limits of success/schema/readback-only checks, not Q1 readiness. TestPlanIt remains the last unexecuted lead in the frozen expansion. Its real host persistence must be admitted and run, or its exclusion recorded, before the finite cohort is assessed. Do not restart Vikunja or add finding-driven repetitions of Fast Dash.
