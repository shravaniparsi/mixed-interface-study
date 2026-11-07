# Protocol amendment v0.2

Recorded after the development feasibility pilot on 6 November 2026 Pacific time. This is a prospective design for subsequent experiments, not a claim of preregistration before the pilot. It supersedes any earlier plan that treats random selection as the only primary comparator or generic API follow-up checking as novel. Numerical budgets and seed counts in earlier planning documents remain provisional until the measurement protocol is frozen.

## Questions and comparisons

1. **Workflow compatibility:** Which reproducible failures arise when a mapped API operation replaces a native UI operation under equivalent actors, versions, lifecycle stages and intended inputs? Describe mechanisms and observed incidence in the eligible corpus, without claiming prevalence across the web.
2. **Value of the UI continuation:** Does executing a native UI continuation expose independently confirmed failures missed by immediate response/schema checks and competent API-semantic follow-up checks? This is a primary comparison. API follow-ups must exercise the corresponding read/update/relation or lifecycle action, not merely request a resource and inspect status 200.
3. **Value of selection:** Under an identical candidate pool, full oracle and execution budget, does interface-specific dependency coverage improve distinct confirmed failure discovery compared with generic dependency coverage? This is the primary selection comparison. Seeded random selection is a secondary reference.
4. **Cost and transfer:** What mapping, annotation, reset, execution and adjudication effort is required, and how does performance change on applications excluded from method development?

Agent-generated API traffic is a motivating deployment setting. A deterministic API runner does not supply evidence about agent behavior. Any later agent experiment needs actual agent runs, fixed tasks, tools, prompts, model versions, costs and a separate analysis. It is not required for the initial feasibility pilot.

## Units and eligibility

Record applications, versions, independent workflow templates, input variants, route variants, repetitions, and distinct root causes separately. Repetitions improve assessment of run variability; they do not increase the number of independent applications or faults.

Before examining failure yield, record whether a workflow has compatible native interfaces, a meaningful mapped operation bundle, equivalent actor permissions, a declared lifecycle stage, a controllable starting state, a visible downstream action, and an external requirement or source-backed interpretation. Record excluded candidates and reasons. The UI is an observation surface, not the ground truth for API semantics. Intentional API drafts, optional fields, normalization and role differences are not automatically defects.

Start with 8–10 development workflow templates across RealWorld and PetClinic as a workload target, not a guaranteed eligible count or statistical sample-size justification. Quartz and Magento are unvalidated held-out candidates; disk and deployment feasibility may require other eligible applications. Record substitutions before observing comparative failure yield. Do not tune the method on held-out failures.

## Experiments

**E0 — Environment and positive controls.** Pin backend/frontend revisions and dependencies. Match logical inputs and verify reset equivalence. Require meaningful edits rather than a save without changes. The present pilot covers two positive-control templates. Expand controls before candidate mutations or strategy comparisons. Standardize fresh-read versus already-open-tab semantics; the accepted RealWorld control requires a new native UI GET after reload.

**E1 — Candidate generation and failure characterization.** Derive candidate constraints from schema, native forms, documented business rules and source evidence. Include valid controls and omission, boundary, enumeration, relationship and lifecycle variants where meaningful. Run only locally controlled subjects. Keep generation inputs separate from adjudicated defect labels. Minimize suspected failures, replay from a reset state, and distinguish environment/runner problems, legitimate interface differences and violated requirements. A UI rejection after API acceptance is only a candidate discrepancy until adjudicated.

**E2 — Oracle comparison.** Use identical prefixes and initial states for paired replays. Compare immediate status/schema checks, API-semantic continuation, and the mapped native UI continuation. Establish equivalent intended actions, actors and permitted lifecycle transitions. Use a shared independent adjudication rubric and report overlap as well as unique confirmed root causes. Equal-candidate replay estimates added diagnostic value; a separate equal-wall-time comparison includes reset, continuation and verification costs. Do not infer practical efficiency from a comparison where one oracle gets unlimited extra time. Record costs of infrastructure state inspection separately; it is not free oracle evidence.

**E3 — Selector comparison.** Random, generic dependency coverage, and interface-specific dependency coverage receive identical immutable candidates, payloads, information and full oracles. Credit only dependencies whose consumption is observed. Use a matched cost estimator for both greedy strategies, calibrated without fault labels; record estimator errors and realized elapsed time. A fixed deterministic tie-break is insufficient for uncertainty assessment, so record paired seeds and ordering. Actual resource-budget enforcement belongs in the runner and is not yet implemented in the selector module. Route coverage is a secondary process measure because it inherently favors a strategy designed to maximize it.

**E4 — Controlled and historical faults.** First validate clean controls. Freeze injected changes and their expected violated requirements before measured comparisons; verify that each fault is active and independently detectable. Avoid constructing every injected fault from the proposed oracle's own rules. Report surviving, equivalent, invalid and setup-failed mutations. Historical issue records require verified repository, buggy/fixed revision pairing, reproduction and a compatible native UI. Keep historical, injected and newly found faults in separate strata. Neither a metadata record nor an issue title establishes a runnable mixed-interface failure.

## Measurement and analysis

Primary outcomes are distinct confirmed root causes discovered at a fixed resource budget, and the incremental confirmed root causes exposed by native UI continuation relative to API-semantic continuation. Discovery curves, time to first detection, false-alarm/adjudication burden, reset failures and author effort support interpretation. Do not count repeated symptoms or repetitions as new faults. Fix budgets, seed count, timeout rules, exclusions, normalization and tie-breaking before measured runs; the pilot is not an effect-size estimate or a power analysis.

Report paired per-application differences and uncertainty, retaining application/workflow clustering. Do not pool repeated executions into a large independent sample. With few applications, descriptive per-application results and an explicit limited scope are more credible than a population-wide significance claim. Any inferential procedure must match the final unit structure. Do not declare a method successful solely because it beats random selection or its own route-coverage metric.

Each competing continuation must start from an independently restored identical post-prefix snapshot, or from an independently replayed identical prefix. Never run the API and UI continuations sequentially on one evolving record. Include equivalent API edits or transitions and read-back checks; distinguish additional observations from different operations.

Keep route-only substitutions separate from payload mutations in both design and reporting. Predefine the joint interpretation of the two primary contrasts; if formal hypothesis tests are used, specify multiplicity handling before evaluation. The default for the small initial corpus is prespecified descriptive effects and uncertainty.

Annotation effort includes operation mapping, requirement interpretation, candidate review and failure adjudication. The study avoids a participant experiment but still needs expert engineering judgment. A separate model review is useful for finding mistakes; it does not substitute for an independent human rater if a paper later claims inter-rater agreement.

## Contribution gate

Active API follow-ups and dependency-derived continuations are established prior work. RESTler active checkers (ICST 2020) and constructed HTTP-semantic scenarios (2026 preprint) motivate the stronger comparisons; verified source details are in `notes/novelty_verification.txt`. A route-labelled greedy selector alone is an incremental extension.

Continue toward a method paper only if the evidence establishes useful native UI/API compatibility failures or oracle value and a substantive benefit against the strongest fair comparator. A null or narrow result may support a different paper framing; it does not justify inflating the claim. Journal quartile is an indexing property, not a guarantee of acceptance or scientific novelty.

## Current execution status

E0 is demonstrated for two templates. E1–E4 comparative experiments have not run. No natural defect has been confirmed, no full benchmark has been assembled, and no agent experiment has run. The selector is implemented and unit checked but is not yet integrated into measured browser executions.
