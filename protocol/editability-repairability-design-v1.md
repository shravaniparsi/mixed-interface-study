# API-created record editability and repairability: design v1

Status: author-approved research direction; prospective design, not a complete
execution registration. The user selected this redesign on 18 November 2026.
No new application, population or evaluation input is selected by this document.
The old catalog study and all its failures remain separate and closed.

## Research questions and intended contribution

RQ1: Among prespecified API-produced states in qualified workflows that are
intended to support UI editing, which support an unrelated ordinary native edit,
and which are rejected, normalized, blocked or changed unexpectedly?

RQ2: For the same prespecified states, does a fixed target-field repair restore
native editability while preserving the intended unrelated edit and the declared
state frame? Compare repair with sham from qualified equivalent starting states.

RQ3: Which outcomes are anticipated by the producer response, original API
schema and competent source-aware validation replay, and where do those channels
remain unavailable or insufficient to determine subsequent UI behavior?

The potential contribution is an empirical account of compatibility obligations,
recovery behavior and the information needed to evaluate them. No novelty claim
rests merely on bypassing frontend validation, inspecting later effects, using
agents, or deriving API tests from UI activity. Findings and a defensible relation
to prior work are still required; Q1 acceptance is not a success condition that
can be guaranteed or manufactured by additional sampling.

## Difference from the closed experiment

The previous estimand was incremental native-continuation information relative
to a complete, matching JSON API continuation. This design measures native
editability and repair effects. HTML forms and JSON producers may coexist: no
counterfactual matching API-update body is invented. Removing that comparator
changes the estimand, rather than satisfying its old gate. Do not retroactively
reclassify old unavailable comparisons as eligible observations.

Full native requests and state effects remain measured. If an API-continuation
comparison is later included, it needs its own fully justified materialization
and starting-state rules. It is not presumed from the producer payload.

## Units, eligibility and compatibility obligation

The sampling unit is a repository lineage; the workflow is the operational unit;
producer variants and repair/sham branches are correlated observations. Report
projects, workflows, input classes and distinct semantic obligations separately.
No variant count may stand in for independent defects or projects.

Require a public OSS application, reproducible pinned executable, local synthetic
fixture, stable-ID persistent readback, API creation and a native editor with two
independently editable scalar text properties. The target and unrelated edit
must not be semantically dependent. Original native creation and ordinary API
creation must both support the intended workflow under the same actor.

Before altered inputs, record why API-created records of this kind are intended
to be editable in that UI: original documentation, explicit integration tests or
an equivalent application contract, with exact source identity. A valid ordinary
control demonstrates feasibility, not a universal contractual obligation. API-only
administrative/import records, deliberate read-only states and different lifecycle
permissions must not automatically be called bugs. When obligation is unresolved,
retain the incompatibility observation and mark defect attribution unresolved.

Exclude real external accounts, personal/clinical/customer data, inter-user
messages, paid services, financial transactions, hardware/GPU dependencies and
third-party side effects. This is not permission to synthesize replacement
application APIs or modify the original validators.

## Inputs and repair fixed before outcomes

For each selected workflow, select up to four eligible target text properties in
UTF-8 JSON-pointer order. Preschedule omission and explicit null plus one shared
ordinary producer control. Use the first other independently editable eligible
text property for the unrelated edit. Freeze literal ordinary values, replacement
values and every property/default before executing altered producers.

For each target, the repair value is its prespecified valid value from the
ordinary native/API control. Freeze the native UI action that sets it. Sham
leaves the target untouched and performs the unrelated edit; repair sets the
target through original controls and performs that same unrelated edit. Apply
this fixed branch schedule to every accepted state, not just cases that appear
blocked. Include the ordinary-state repair control. Missing, disabled or
unsupported repair controls yield repair_unavailable; never force them enabled.

Do not choose a new repair from an observed error message or add variants after
finding a failure. Target-only repair may still have declared dependent effects;
those effects must be identified before outcomes, not excused afterwards.

## Observation contract and labels

Preserve producer request/response, independent persistence/readback, actor and
lifecycle evidence. Do not infer rollback or correctness from HTTP status alone.
Record producer rejection, accepted unchanged value and accepted normalization
separately. A 2xx response without confirmed persistence is not an accepted state
for continuation analysis.

On continuation record actionability, validation events/messages, enabled state,
all emitted native requests/responses, complete relevant state and ancillary
effects. Distinguish successful intended edit, browser/client blocking, emitted
native-request rejection, unintended write, authentication/authorization failure,
stale-state conflict, unavailable observation and setup failure. Record normalized
values as data; normalization is not inherently an error.

A blocked classification needs positive evidence of a native blocking mechanism,
no relevant emitted request within a prospectively qualified observation window,
and preserved state. The authored fixture's 500-ms window is not a universal
choice for real applications. Unsupported asynchronous validators or unresolved
pending work make the result unavailable, not proof of blocking.

Successful edit requires independent readback of the intended unrelated change
and preservation of the declared frame, with exact predefined derived effects.
Repair success additionally requires the specified target value and all permitted
repair effects. Preserve missing versus null and boolean versus number distinctions.

## State equivalence and causal interpretation

First qualify an ordinary warm continuation and its restored-sham equivalent.
Publish the application-specific state scope and restore procedure: database,
files, caches, queues, actor/session, browser storage, loaded form and relevant
background activity. The authored file-only fixture is not that qualification.
Compare full relevant starting state and original native request behavior; retain
all differences. An exception requires an operation-specific rationale and check
published before outcomes. Never infer warm equivalence from two restored branches.

For accepted altered states, sham and repair start from the same qualified
checkpoint. Confirm state and actor before editing. Repair changes only the
prespecified target control before the otherwise identical native action. Record
all actual request differences and resulting state. Where the target repair
changes other unaccounted conditions, call attribution unresolved.

If sham blocks and repair succeeds with the complete expected state effects,
report evidence that this fixed intervention restores the specified edit under
these conditions. This is not proof of a unique root cause, universal repair,
backend validation defect or superiority of one testing algorithm.

## Competent comparison channels

H: producer response plus independent persistence observation. Retain both;
response status alone is not a correctness oracle.

S: the original API schema under its qualified dialect and actual validator
semantics. Unsupported or absent obligations remain unavailable. Do not import
frontend rules into the schema baseline.

D: replay of original source/native validation with the same declared field,
actor and lifecycle information available to the study method. Freeze its
coverage, dependencies and execution before outcomes. Unsupported replay is
unknown, not a wrong prediction. Handwritten rules must be labelled as such.

U: actual ordinary native continuation and its state effects. Compare agreement
and missingness across these channels, preserving their different targets and
information access. Do not count agreement with D as a method advantage or
promote H/S/U descriptive results into superiority over an unexecuted D.

## Sampling, effort and execution gates still to instantiate

Before selecting an empirical cohort, publish a new sampling justification tied
to this question, immutable population/revisions, deterministic workflow ordering,
updated exposure/lineage rules, development/evaluation separation and all exclusions.
Do not simply take the next untested catalog entries until failures appear.
Old closed projects cannot silently return as independent evaluation systems.
Historical exposure gaps remain disclosed; absence from an index proves no
absence of exposure. Refresh known references before selecting candidates.

The concrete registration must state acquisition/adapter effort limits, separate
ordinary qualification and scientific execution budgets, a fixed allowed number
of infrastructure corrections, per-job timeouts, total project/case ceilings,
stop conditions, evidence retention and all literal inputs. Track active manual
review and agent/tool preparation separately; cheap runner time is not low
manual effort. Preserve the $100 project ceiling and permit no new paid services.
No unspecified acquisition or execution slot is authorized by this draft.

Useful null evidence requires qualified controls, sufficient covered obligations
and complete denominators, not simply zero detected failures. High qualification
attrition is a feasibility result. Report all exclusions, missingness, failure
stages and unresolved ancestry. Statistical analysis and uncertainty rules must
be frozen with the actual sampling design; do not pool correlated branches as
independent trials.

## Current execution decision

The direction is approved; the empirical study is not yet executable. Next
resolve an outcome-independent, feasible population and competent baseline
coverage, then publish the complete registration and per-workflow recipes before
any altered-input outcomes. No result, defect count or journal-readiness claim
has been added by this redesign.
