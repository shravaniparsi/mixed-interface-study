# Multiworkflow evaluation: prospective freeze gates v1

**Status: planning protocol; primary evaluation freeze is not complete.** This document defines the next empirical milestone. It reports neither comparative effectiveness nor final runtime-validation results.

## Next milestone

Prepare and freeze a multiworkflow candidate corpus for paired API-semantic and native UI continuation evaluation. Establish the additional observations supplied by native UI continuation before making selector-effectiveness claims.

The current development inventory contains seven templates: RealWorld article create→body edit, article update→comment creation, comment create→delete, and profile update→meaningful settings edit; PetClinic owner create→address edit, pet create→rename, and visit create→reschedule. Use the eligibility ledger to retain, split, or exclude these mappings with reasons. Route variants, payload variants, repeated runs, and multiple symptoms do not create additional independent templates or applications. Seven is an inventory, not a sample-size requirement.

Quartz prospective v2 adds a stored-job create→description-edit template with a source-registered accepted-state stratum, alongside rejection controls. Its exact variants and exclusions must be registered before their execution. The earlier required-class-only pool does not provide sufficient accepted-state variation for this milestone.

## Gate 1 — Provenance and eligibility

- Label reused RealWorld/PetClinic observations and candidates as development evidence. New execution of a previously examined case does not make it untouched evaluation data.
- Record Quartz source inspection, deployment work, and ordinary positive controls already performed. Distinguish boundary cases not yet executed from a wholly unseen application. Its evaluation status requires no outcome-driven changes to the frozen generator, oracle rules, or selection method; subsequent tuning would require a later untouched evaluation set.
- For every template, record versions, artifacts, actor and permissions, lifecycle state, reset procedure, meaningful operation bundle, resource bindings, preservation obligations, and requirement sources. Record unsupported representations and exclusions before comparative outcomes are inspected.
- Register the finite constraint/operator catalog, accepted-value and normalization controls, and rejection probes. Preserve original registries when expanding scope. Do not select variants because their outcomes look favorable or require a quota of failures.

## Gate 2 — Freeze the experiment and validate execution

Freeze candidate content, adapter and method versions, requirements, expected normalizations, coverage definitions, oracle checks, cost scope, timeouts, interruption policy, ordering, and replay rules. Hash the resulting artifacts and record the actual environment. Runtime validation, including deadline interruption, owned-process cleanup, and a successful subsequent fresh reset, must pass before timed evaluation. Preserve failed attempts and corrections; do not silently replace them with successful reruns.

Require native UI requests to arise from ordinary controls. Capture actual payloads and resolve consumer identities and unchanged fields from accepted producer state. Confirm that adapter normalization does not repair the condition under study. Verify clean controls and independent resets. A rejected producer stops its continuation and earns no downstream coverage; retain status, body, and observable post-request state.

## Gate 3 — Paired oracle evaluation

For each eligible prefix, independently restore the same starting state and replay the same prefix for each continuation. Compare immediate response/contract observations, the corresponding API-semantic read/action/readback, and the native UI implementation of that same intended action. Never apply both continuations sequentially to one evolving record. Keep fresh-session semantics fixed.

Use a common requirement-based adjudication rubric. API acceptance, a UI rejection, or disagreement between interfaces alone does not establish a defect. Distinguish intended capability differences, defaults, normalization, permissions, unreadable state, application failures, and adapter/environment errors. Repeat candidate failures with their nearest valid controls from fresh resets.

Report paired outcomes by template and distinct root cause: detected by both continuations, API only, UI only, neither, or unresolved. Keep known/reproduced issues, historical buggy/fixed cases, injected faults, and faults whose prior-report status is unknown in separate strata. Repeated symptoms and issue duplicates remain one root cause. Independent human adjudication is pending; AI review is not human inter-rater agreement or maintainer confirmation.

Report eligible, attempted, accepted-prefix, reached-continuation, completed, blocked, and timed-out cases separately. Record reset, startup, authentication, operations, verification, evidence-capture, and teardown costs, with shared setup disclosed separately. Equal-candidate oracle comparisons establish diagnostic differences; practical efficiency requires a separate common wall-time comparison. Unfinished or late results cannot silently become passes or credited work.

## Gate 4 — Selector evaluation remains a later decision

The single-workflow pools validate integration, not selector efficacy. Before a primary selector comparison, assemble a frozen multiworkflow pool with multiple dependency structures, paths, and accepted-state conditions. Document its structural diversity and eligible failure evidence; do not manufacture independence through extra seeds or duplicate routes.

Freeze the custom generic-dependency selector as the primary comparator, route-obligation selection as the proposed method, and random selection as a secondary reference. All receive the same candidates, permitted feedback, calibrated costs, full oracle, and actual execution budget. Calibrate without fault labels. Credit observed dependency consumption, including defined failing-consumer cases, while excluding oracle-only probes and unexecuted consumers. These custom comparators are not executions of RESTler or other published tools.

Primary future outcomes are distinct adjudicated root causes within the declared budget and paired oracle detection overlap. Route coverage is a secondary process measure. Report per-application/workflow results, costs, uncertainty where justified, and unresolved cases; repeated executions are not independent applications. No efficacy, prevalence, agent-behavior, or broad transfer claim follows merely from passing these gates.

**Freeze completion requires an explicit dated record linking the final corpus, protocol, code, environment, and unresolved adjudication items. This document does not supply that record.**
