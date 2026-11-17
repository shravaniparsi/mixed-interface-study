# Candidate method: transfer constraints with their applicability conditions

Status: prospective method specification, not a claim of novelty, registered application cohort or authorization to rerun closed studies. The question is whether frontend evidence improves API-test oracles at a useful acquisition cost when legitimate interface differences are retained. The broader original workflow-compatibility question remains open; this candidate is a possible method contribution toward it, not a replacement success criterion.

## Inputs and output

Input is a pinned application revision, an operation, frontend validator/source location, an explicit field-to-request/state mapping, any documented serialization/defaulting transformation, operation/actor/lifecycle conditions, API specification, and independently authored task requirements where available. Each input has provenance and exposure status. No issue fix or held-out test outcome may be used to construct evaluation predicates. The current historical null example is development-only.

The output is a conditional predicate over a specified request, response, or post-operation state, with source locations, applicability condition, transformation assumptions and a reason for unsupported cases. A rule does not become a global API invariant merely because a form uses it. Frontend constraints supply evidence of that workflow's requirements; independent task/contract evidence is needed to label a violation as an intended-behavior defect.

## Transfer procedure

1. Extract explicit supported validators and their guards. Retain presence, range, enumeration and length semantics separately. Never infer requiredness merely from a label or field name. Record unsupported cross-field callbacks and asynchronous checks rather than approximating them silently.
2. Resolve the field mapping through explicit serialization/binding evidence. An identical name alone is insufficient. Distinguish request omission, JSON null, empty string and serialized defaults. Keep the mapped operation, actor and lifecycle scope.
3. Compose the predicate with a known transformation only when its semantics are represented. A frontend length measured in one string representation cannot silently become a different backend length measure. An unknown transformation produces unknown applicability, not a stricter predicate.
4. Choose the observation point according to the rule: submission requirements apply to the relevant request; persisted-state obligations apply after the producer at the registered readback point; later consumer preconditions are attached to that consumer. A successful API response alone does not establish that readback timing is valid.
5. Evaluate only when mapping, applicability and required observation are known. Otherwise emit unknown with a specific reason. Exceptions remain code_error. Source conflicts remain unresolved unless independent requirements resolve them; do not choose the stricter rule by default.

This is currently an algorithm specification. Raw-source extraction, mapping, transformation reasoning and a complete end-to-end adapter are not implemented. If those are supplied manually in a pilot, report it as manual-input transfer evaluation, not automatic constraint acquisition.

## Comparisons that isolate the claimed value

A: competent API-specification oracle mining, with its documented inputs and semantics. Current RBCTest is a candidate implementation; it remains unqualified for this project.

B: direct frontend-rule transfer using the same acquired rules and mappings as C, without preserving applicability distinctions. This is a diagnostic ablation only, not the strongest baseline and not a substitute for A or D.

C: the conditional transfer procedure above.

D: a practical source-aware comparator given the same frontend, API, task and mapping evidence as C, with the same call/token/time allowance. It must be specified and qualified before evaluation. A simple direct implementation that preserves the same guards may be equally effective; C must not receive privileged evidence or cheaper uncounted setup.

E: independently justified manual contract reference, with annotation costs reported. This supplies a reference outcome where adequate, not an automatic competitor or infallible truth.

A versus C measures the value of additional evidence plus processing. C versus D measures method benefit at matched information. B versus C diagnoses whether applicability handling matters. Keep these claims separate. If C is merely an implementation of D's existing logic, make no algorithmic novelty claim; a sufficiently rigorous empirical result may still be useful, but that is unproven.

## Falsifiable predictions and stopping decisions

Primary candidate prediction: C reduces incorrect alerts relative to B without losing violation detection through excess abstention. That alone is insufficient for a new-method claim. C must also demonstrate a useful accuracy/coverage/cost tradeoff against D, across independent project clusters, under a prospectively chosen effect target and uncertainty analysis. No effect size is selected here without a feasible sample frame.

Reject the claimed practical advantage if gains disappear under matched information, are explained only by abstention, depend on issue/label access, require uncounted manual mapping, or arise only on authored synthetic examples. If observed rules cannot be justified independently, retain unresolved labels and do not call agreement with the frontend correctness. If the proposed method has no distinguishing operation beyond established conditional checking, retain it as an engineering baseline and stop presenting it as novel.

Development falsification cases must include optional empty values; create-versus-update requiredness; explicit null versus omission/defaulting; conditional field relevance; role-specific restrictions; known serialization changes; unknown mappings; contradictory requirements; and ordinary valid states. These are analyst-designed engineering tests, not externally discovered defects or an independent sample. They cannot establish scientific usefulness.

## Dataset and budget gate

No corpus is selected by this specification. Before collection, freeze an externally defined project/workflow frame unrelated to observed failures, eligibility rules, all exclusions, unit/cluster definitions, exposure split and label sources. Separate successful installation from experimental eligibility. Do not pool the earlier application, issue, mutant and component denominators into this study.

The original $100 ceiling remains. No model-backed comparison starts until its call budget, acquisition effort, baseline mode and remaining project costs are recorded. Unpaid assistant assistance is not evidence of reduced human labor. If both method and baseline cannot be evaluated competently within the remaining resources, report that limitation rather than weaken the baseline. Nothing here authorizes third-party messages or production writes.

Implementation status, 2026-11-17: the conditional evaluation stage is now implemented in src/mixed_interface/constraint_transfer.py for explicit caller-supplied rules and mappings. This post-specification status note does not retroactively claim automatic extraction or end-to-end qualification. See notes/constraint_transfer_implementation_20261117.md.
