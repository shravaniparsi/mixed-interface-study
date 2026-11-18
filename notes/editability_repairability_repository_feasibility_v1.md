# Frozen redesign candidate split and repository metadata

The forty passing metadata candidates were deterministically ordered and split
into eight development candidates and thirty-two evaluation candidates before
new repository metadata collection. The schedule and collector were published at
2ff1e2505c1b741d7d7bbf14a945ee97c9855596. No project moves between groups and no
replacement is allowed. Later workflow caps are two development and six evaluation,
subject to source eligibility and separately frozen execution rules.

One bounded collection completed all 120 scheduled requests. Each repository
matched its canonical name, was public and not marked forked, archived or disabled,
and yielded a default-branch commit and a nontruncated recursive tree. Retained
responses total 17,006,896 bytes, below the 64-MiB stage cap. The verifier checked
response SHA256 identities, endpoint/ref/tree bindings, complete forty-row coverage
and the hash-derived order and split. Repository elapsed times sum to about
60.22 seconds; this is metadata request/processing time, not experiment cost.

All forty rows remain metadata_pinned_workflow_unqualified. These flags and owner
labels do not establish independent ancestry, compatible UI/API contracts,
editable fields, executable provenance, deployment, state restoration or usable
source-aware validation. The tree response locator is recorded separately and
is not asserted to be the root Git-tree hash.

Development order: enterpilot/gomodel, diced/zipline, kong/kong,
defilantech/llmkube, kovah/linkace, dani-garcia/vaultwarden, judge0/judge0,
mediacms-io/mediacms. This is a candidate order, not a finding-ranked shortlist or
selection of two workflows. Earlier unresolved candidates must remain unresolved
if a later candidate qualifies. Evaluation outcome inspection cannot guide
method construction or repair rules.

The next stage needs published per-project source/path schedules and acquisition/
effort bounds. Start with the development group to establish original workflow,
contract, baseline and deployment feasibility. No application execution, source
content acquisition or scientific case occurred in this metadata stage. The old
catalog study remains closed and no old failure was reinterpreted.

Recheck the retained metadata without network or application execution:

    PYTHONDONTWRITEBYTECODE=1 python3 scripts/extension/verify_redesign_repository_metadata_v1.py
