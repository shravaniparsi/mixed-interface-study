# Corpus review after paired database qualification

The review preserves 73 paired catalog entries, two native-only controls, 148 logical branch slots and eight workflows. Forty-four entries now have named engineering evidence, up from 41 in the baseline map. Evidence coverage is not primary-dispatch readiness or an independent sample count.

Five identity entries have qualified observed paths. Four have same-branch database captures; empty username has a completed rejection observation from the older halted campaign. The generic “identity helper missing” labels are stale for these exact observed paths. Three identity entries still need integration into a general primary campaign, and null/empty rejection observations do not cover unexpected acceptance. The older coverage map remains intact; `manifests/retained-corpus-review-v2.json` carries the reconciled requirements and evidence.

## Remaining implementation work

| Work package | Retained entries affected | Required next action |
| --- | --- | --- |
| Remaining legacy RealWorld | 7: five pairs and two native-only controls | Bind title lengths 150/151, whitespace title, duplicate-title partial/full updates, and the two native-only controls to versioned extraction and dispatch. Preserve singleton accounting. |
| Generated RealWorld | 9 pairs | Bind the existing generated inputs, normalization and terminal extraction to immutable paired jobs; preserve producer routes and exposure strata. |
| Identity primary integration | 3 pairs | Integrate null and 60/61-character usernames into the primary campaign without converting the bounded diagnostic into a primary result. |
| Unexpected acceptance | 8 rejection entries | Define and qualify the accepted-response paths, including explicit inability to bind a continuation. Never coerce invalid input to make a continuation succeed. These entries overlap other work packages. |
| Quartz selection and batching | 20 mutation pairs, 40 untouched branches | Prepare exact primary selection and bounded batch accounting before execution. Keep both ordinary reference controls and all exposure labels. |

These counts must not be added as disjoint samples. Unknown requirements and incomplete semantic outcomes are separate from missing implementation. Two identity policies remain unresolved; the 61-character case remains semantically incomplete. PetClinic retains two unresolved-policy entries and two incomplete-response entries. The final rubric must retain these categories; it must not demand invented product requirements or exclude difficult cases after observing outcomes.

## Cost decision and remaining gates

The prospective amendment in `protocol/primary-cost-scope-v2.md` selects monotonic end-to-end branch elapsed time for the initial equal-candidate diagnostic comparison. Cross-workflow exclusive-phase and isolated action-speed claims are deferred. Existing phase records and the later equal-budget selector study remain unchanged.

The inspected RealWorld v7 and Quartz v2 runners already expose candidate monotonic branch totals. PetClinic v3 does not: request durations and ISO timestamps cannot be added together to recover the missing interval. A new PetClinic runner must add that boundary and verify failure/cleanup accounting on exposed controls. New RealWorld paths must adopt the same scope; database capture overhead remains included and source-specific timings are not pooled.

P2 remains open for the bindings above. P3 needs immutable batches, complete/failed/missing-batch accounting and deterministic post-sweep repeats. P4 now has a concrete scope decision but still needs instrumentation coverage and preflight enforcement. P5 follows those steps with the final source, corpus, requirement, schedule, environment and cost freeze. No new application run or primary sample was added by this review.

Next implementation priority: the five remaining legacy RealWorld pairs and two native-only controls, while preserving all existing qualified paths. Batch planning and the PetClinic timer can proceed without consuming untouched boundaries. Further blanket lifecycle campaigns for unchanged runners are not required.
