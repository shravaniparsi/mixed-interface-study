# Production application extension, registered 10 November 2026

## Objective and relationship to the completed study

The completed collection is exploratory evidence and engineering validation. Its original data, invalid measurements, qualification failures, and null corrected results remain unchanged. This extension asks whether API writes leave objects usable through their native web editing workflows, and what native continuation testing observes beyond competent API-semantic checks. It does not claim that client/server validation inconsistency, workflow-aware tampering, or downstream client harm is a new problem.

The primary candidate contribution is a reproducible empirical benchmark and comparison of observation methods. A method-effectiveness or mitigation claim requires its own measured comparison. Merely attaching an MCP wrapper or increasing a case count cannot establish such a contribution.

## Application selection before boundary execution

The six subjects are linkding, Vikunja, Memos, Gitea, Paperless-ngx, and Grocy. They were selected purposively for self-hostability, native web editing, API support, production use rather than being solely teaching applications, and domain diversity. The dated screening registry pins stable release tags and source commits. This is not a random sample of web applications. Documentation and preliminary issue-search exposure are disclosed; none is described as an untouched application.

All six enter the feasibility ledger. Keep failures and zero-finding applications. A failure to deploy within two bounded engineering attempts is an exclusion with an explicit technical reason, not a reason to substitute a more promising application. A change to the subject list requires a dated amendment before examining that replacement's boundary outcomes. No live third-party demo is a test target.

Stage A only pulls a release image, records its resolved digest, starts an isolated local instance on a hosted runner, probes HTTP reachability, and confirms cleanup. HTTP reachability is neither adapter qualification nor application correctness. Digest and application version must be verified against the selected release before any scientific run. The first resolution may use a release tag; subsequent qualified runs must use the recorded digest.

## Workflows and finite input inventory

Stage B inventories existing resources with both documented API create/update operations and native edit/save actions. Register two to four ordinary workflows per application where supported, with all exclusions recorded; a field variant is not a new workflow. Prefer domain resources, not authentication bypasses. Initial resource candidates are bookmarks (linkding), tasks/projects/labels (Vikunja), memos and documented editable settings (Memos), issues/milestones/labels (Gitea), correspondents/document types/tags (Paperless), and products/locations/tasks (Grocy). Actual eligibility and API/UI bindings must be established from the pinned version before the inventory is frozen. Do not add resources because they produced interesting failures.

Each workflow has an explicit actor, starting fixture, producer operation, ordinary unrelated continuation edit, preserved fields, allowed normalizations, and persisted-readback contract. Extract constraint candidates from observable native form attributes and source-qualified custom validation; record the provenance and unsupported constraints. Every extracted constraint needs an ordinary valid control and a deliberately violating adapter-control input. DOM extraction must independently agree with raw request payloads and persisted fields. Empty extraction is not absence of a constraint.

Generate a deterministic finite inventory from the registered constraints: omission/null/empty where applicable, values at and immediately outside numeric or length bounds, invalid enum values, reference absence, and source-declared cross-field boundaries. Apply only type-compatible transformations. Include interior valid controls. Cap at 12 boundary variants and four valid controls per workflow (maximum 384 candidates for 24 workflows); if more exist, select by stable seeded ordering within constraint families, before execution. Freeze the complete generated inventory and the unselected remainder. Accepted and rejected writes both remain in the denominator. No mutation tuning after examining outcomes.

## Observations and baselines

For each candidate, independently reset and replay an identical producer write for each continuation. Match actors, payloads, initial and post-prefix business state; record normalization exclusions in advance. A producer rejection cannot be a continuation failure. An HTTP success must be verified by persisted resource identity and state.

Compare the following observations without attributing shared probes exclusively to one channel:

1. Immediate status and documented response/schema checks.
2. API-semantic continuation: read, perform the same meaningful edit as the UI branch, read back edited and preserved fields, and check failed-write side effects when applicable.
3. Native continuation: open the actual editor, observe loaded values and validation state, change only the registered unrelated field, save using native controls, then obtain fresh persisted readback.
4. Constraint-consistency signal: whether the producer value violates a registered client-side constraint. This is an established kind of baseline, not a reproduction claim for NoTamper or WARDroid. It predicts potential incompatibility but is not itself an observed defect.

Primary outcomes distinguish accepted/rejected/incomplete prefixes; editor load failure; correctly loaded but blocked save; successful save with unintended preserved-field change; successful preserving continuation; and execution/policy uncertainty. A GUI failure due to an incorrect selector or incorrectly filled field is an adapter failure. A documented intentional normalization is not corruption. Report observable inability to complete the prescribed task separately from a requirement-backed defect assertion.

Repeat every candidate with a channel difference, preservation discrepancy, or execution uncertainty twice with the original valid control from fresh resets. Retain variability and all failures. Repeats do not increase the number of independent mechanisms. Do not repeat clean observations until they fail.

## Analysis, mechanisms, and limits

Report complete funnel counts and API-only/UI-only/both/neither overlap by application and workflow, alongside unresolved and rejected outcomes. Use application-level summaries; candidate variants and repeats are correlated. Do not report population prevalence or a pooled significance test from six purposively selected subjects. Record setup and each observation component's actual wall-clock cost. No timing comparison may inherit UI work in an allegedly API-only baseline.

For each reproducible differential, create a minimal causal packet: original trace, ordinary control, affected and unaffected fields, source-based mechanism, requirement authority or unresolved policy, and counterfactual repair if feasible. The repair experiment changes only the implicated input or a separately identified application patch; the original evidence remains immutable. Historical known faults and injected adapter controls are separate cohorts and cannot be counted as new natural defects. Search issue history before any novelty label. No issue, email, or disclosure message is sent without user authorization.

A prospective experiment may subsequently compare a constraint-derived preflight guard with schema-only checks, but only after freezing that guard on development applications and defining held-out application evaluation. It must measure prevented failures, valid writes incorrectly blocked, and overhead. Testing a guard only on its own construction cases does not establish efficacy. Likewise, an LLM-agent success claim requires actual agent trials; deterministic API replay makes no such claim.

## Resource bounds and decision rule

Use standard public hosted runners, at most three simultaneous app jobs, isolated synthetic fixtures, and the existing $100 total cash ceiling. No paid model API usage is authorized by this protocol. Stage A has at most two 20-minute attempts per subject. Plan the full case execution budget after ordinary controls provide empirical runtime estimates, before launching boundary cases. Keep a recorded execution limit rather than running until a desired effect appears.

Coverage of all feasible registered subjects and candidates is the stopping rule for this extension. If the data mostly show clean behavior or API checks already detect the relevant failures, report that result and assess an empirical/benchmark contribution honestly. A claim of broadly useful incremental native testing needs consistent support across applications and reproducible mechanisms, not a selected anecdote. No fixed bug count, p-value, or number of CI jobs guarantees Q1 suitability. A substantive novelty and evidence review follows the frozen experiment, with an explicit no-go conclusion if warranted.
