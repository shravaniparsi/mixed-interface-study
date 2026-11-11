# Bounded historical write-contract corpus expansion v1

Status: source-admission protocol; no new runtime cases registered by this document. Date: 2026-11-11. Existing Tiller and Iris artifacts are immutable development data.

## Scope and exposure

The purpose is to assess feasibility and utility of a real-defect benchmark, not to estimate ecosystem prevalence or unseen detector efficacy. All six leads below were exposed through issue/patch-oriented searches. No project is called held-out. The order and stopping rules are fixed before further implementation. Historical issue labels are leads, not ground truth.

| Order | Project / record | Current status |
|---|---|---|
| 1 | webern/tiller-sync issue 40, PR 45 | Completed: 12 executions, one known mechanism |
| 2 | cgbarlow/iris issue 314 | Completed: 24 executions, one known mechanism |
| 3 | apache/superset PR 44188 | Patch inspected, runtime unexecuted |
| 4 | go-vikunja/vikunja issue 4109, PR 4166 | Report/patch metadata inspected, runtime unexecuted |
| 5 | dkedar7/fast_dash issue 191 | Report inspected; fix and admissibility unverified |
| 6 | TestPlanIt/testplanit issue 668 | Title screened; fix and admissibility unverified |

No substitutions after runtime failures or unfavorable results. If a lead is ineligible, retain its reason and continue in order. New leads discovered during this work enter a future proposal only; they do not replace this cohort.

## Admission and execution

For each remaining lead, first establish the public source/license, immutable historical commit and repair, a documented preservation obligation, runnable local synthetic fixture without paid services, and an independent persistent-state observation. Reject a case if the purported bug is only expected replacement semantics. Record ambiguous contracts as ambiguous rather than assigning a violation label.

Before dispatch, commit an application-specific protocol specifying fixture, request, observations, intended assignments, derived changes, control cases, source/dependency pins, baseline implementations and correction allowance. Inspecting a known patch is allowed and logged. That registration freezes the experiment, not unseen discovery. Use real production entry points and storage; mocks cannot qualify the scientific defect. State exactly which wire, dispatch, API and database layers execute.

Use the historical/fixed pair and, where technically isolatable, adapter/backend interventions. Do not manufacture hybrid cells when the components cannot be separated. Include the reported operation, an ordinary valid control, and an explicit-clear or legitimate-cascade control when the application supports one. Unsupported controls remain inapplicable, not successful.

Baseline set: advertised schema, reported operation success, requested postcondition, manually specified frame. A payload-presence rule is included only when its input-to-state mapping is specified; it is not presumed correct for full replacement, defaults or cascades. If a newly proposed automated method is later introduced, its independent evaluation needs a separate protocol and different data.

Record all target-row changes, plus related entities required by the case's obligation. Persist fresh readbacks and a downstream query when feasible. Source-derived expectations are not runtime observations. Preserve failure logs and infrastructure exclusions.

## Limits and stopping

For each of four new leads: at most one initial application run and one instrument correction, at most four runner jobs per attempt and 15 minutes per job. Stop dispatching when their aggregate elapsed application-job time reaches 100 minutes; if a running wave crosses the ceiling, retain it and dispatch no further wave. No paid model or cloud calls. Use existing free standard public Actions within the overall $100 project ceiling. Unit verification is accounted separately.

A correction may repair harness/fixture compatibility only; it cannot change the scientific operation, remove a failing control or weaken the oracle. Otherwise register a new protocol and report the initial result. No repeated runs for stronger statistical significance: execution variants are not independent defects.

After all four leads are admitted/excluded, or the time ceiling is reached, stop this expansion and assess:

- transfer of the common trace format and checker, with the amount of per-case code and manual contract mapping disclosed;
- additional mechanisms and controls actually observed, with counts clustered by project and root cause;
- utility relative to MCPEvol-Bench, DCI and RESTestBench, including overlaps and absent features;
- whether a concrete reuse task is supported, such as validating a repair without breaking intentional clears.

Two more known-case reproductions alone do not establish a Q1 contribution. If the corpus remains small, highly specialized or redundant with available artifacts, report that result and do not label it submission-ready. A positive benchmark-utility decision still requires an external-facing evaluation and manuscript review before submission.
