# Development reuse audit after catalog closure

The previous cohort remains closed. This review ran existing synthetic baseline
tests and examined their implementations; it did not execute any application,
reopen a qualification attempt or generate a scientific case.

## Executed findings

Twenty-two existing write-related tests passed. Source inspection then found
that write_observations.measure uses Python == for intended values, complete
projection comparisons and restart comparisons. Python equates False with 0
and True with 1, including inside containers. This can report a type-changing
projection as unchanged, an unachieved typed assignment as achieved, and a
changed restart projection as preserved. The passing suite did not cover this.

Added write_observations_v2 with the existing type-sensitive JSON comparator
from write_frame. It preserves v1 input validation and detached output records,
recomputes the three measurements and emits schema_version 2. Version 1 and all
historical callers remain unchanged. New regression tests reproduce the old
behavior and verify the correction in both directions for scalar and nested
boolean/number pairs. They also check intended type-changing writes, missing
observations, ordinary-string agreement and nonfinite JSON rejection. All 27
write-related tests pass. These are engineering controls, not independent
scientific evidence or a new application defect.

Known historical callers are replay_write_observations.py,
realworld_identity_measurements_v2.py and realworld_identity_database_job_v7.py.
Their complete retained-output impact has not been reanalysed. Do not claim that
historical results are affected or unaffected without examining actual inputs.
No old result is relabelled and no caller is silently upgraded. The new module
also depends on the retained v1 validation and write_frame equality code; the
reuse manifest hashes all three sources, not just the new wrapper.

## What is reusable and what is not

write_frame and write_contract provide manually supplied assignment/preservation
checks. They do not infer application obligations, acquire UI rules or establish
that the measured projection covers all relevant state. write_observations_v2
separates HTTP response, persisted observations and restart persistence, while
explicitly leaving continuation not_measured. These components can support a
future development harness; none replaces a native browser adapter, actor/state
qualification, a competent baseline or causal adjudication.

The older terminal_outcomes policy permits repeats for some failure types. It
cannot be reused as a dispatcher under the catalog no-rerun protocol. No such
policy was activated by this review.

## Next concrete gate

Before any proposed new independent sample, test the complete observation path
on a deliberately authored development fixture with known labels and genuine
ordinary browser controls. Required controls must distinguish: successful
continuation; backend rejection; accepted and normalized input; native validation
blocking an unrelated edit; authentication failure; stale-state conflict; an
unintended extra write; and missing observation. Prespecify all fixture states,
expected labels, snapshots, actor checks and any repair intervention before
execution. Fixture truth is engineered and must never count as natural defects.

First investigate the historical typed-equality impact using retained records,
without application reruns. Then write the concrete development fixture protocol
and execute only after its own prospective publication. That work can determine
whether a later-UI-editability measurement is reliable; it cannot establish
novelty or authorize another positive-seeking cohort. The exact-request catalog
comparison is not relaxed or retrospectively replaced.
