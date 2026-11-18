# Redesign repository feasibility and fixed split v1

Use all forty repositories passing the published metadata screen. No replacement,
new catalog entry or changed API-advertising rule is allowed in this stage. The
population is the API-advertising metadata stratum already described, not all web
applications. The user approved the new question; the old failed cohort stays
closed. This stage collects only repository metadata, a default-branch commit
and recursive path tree, not source contents, issues or application outcomes.

Before collection, order the forty repositories by SHA256 of UTF-8
`editability-repairability-feasibility-v1|114743487b2cfd1a9c68deff3511c11c3b307695|`
followed by the normalized repository. Tie-break by repository. The first eight
are development candidates and the remaining thirty-two evaluation candidates.
Freeze these assignments now. Do not move failures between groups, train a
method on evaluation outcomes or fill a development shortfall from evaluation.
Prior metadata references are disclosed; these groups are not called source-blind.

The intended later maximum is two development workflows and six evaluation
workflows, selected in their group's fixed order from prospectively established
source eligibility. This is not selection now: no project is known eligible.
Retain unresolved prefixes and never call a later qualifying workflow the first
eligible if earlier candidates remain unresolved. Freeze the actual selection,
full baselines, workflow recipes, controls, literal inputs and analysis before
any evaluation outcomes. No substitution after runtime/control failure. Source
qualification limits and runtime effort/time budgets require their own published
instantiation before those stages; none is granted by this metadata collection.

Per repository, at most three sequential GitHub API requests: repository metadata,
declared default-branch ref and recursive tree at that exact commit. Thirty
seconds per request, ninety seconds per repository. Response caps are 1 MiB for
metadata/ref and 8 MiB for tree; all retained responses combined <=64 MiB. Process
repositories in frozen order. No retry, alternate branch, mirror, clone, content
read or repository substitution. Failures remain unavailable and the next fixed
repository proceeds. Stop further requests if the total retained-byte cap is
reached; keep every unattempted row visible.

Require canonical full_name to match the requested repository case-insensitively,
visibility public, fork false, archived false and disabled false. Stop that row
at metadata if any of these fail. Preserve parent/source identity and the original
response. A rename is an alias-review hold, not automatically independent. These
flags do not prove absent shared ancestry: lineage remains unresolved pending
source/provenance review, including relation to historical exposures and the
other candidate group. If later shared lineage is found, conservatively group
or quarantine before outcomes; do not promote replacement projects.

Reject missing refs or truncated trees. Record the commit and tree response
locator explicitly; do not assume the tree endpoint's response SHA is a root
Git-tree hash. Bind all requests, response sizes and SHA256 digests, failures and
elapsed times. Check schedule, protocol, collector and input evidence against
the published freeze before requests. No runtime is launched and no new
scientific input or sample is counted by this stage.
