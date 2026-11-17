# Full instruction-frame eligibility screen

All 175 archived task instructions have now been reviewed in lexical task-name order under protocol/agentcompany-instruction-eligibility-v1.md, frozen at aad95bb37de7aea441962dd667aea1b918b76c38. The protocol SHA-256 matches the committed version. The task catalog, source revision, per-instruction hashes, labels, explanations, response requirements and candidate dependencies are retained in manifests/agentcompany-instruction-screen-v1.json. This was one AI-assisted analyst pass, without independent human adjudication, application execution or grader inspection.

The prior turn made progress by preserving image metadata and freezing these rules. This turn completed the full instruction review. No scientific outcome has been added, and no previous cohort has been reopened.

| Primary instruction code | Tasks |
| --- | ---: |
| Explicit chain | 20 |
| Conditional or conversation-dependent chain | 22 |
| Ambiguous chain or conflicting requirements | 15 |
| Web writes without a specified produced-state consumer | 66 |
| No benchmark web-state write | 52 |
| Total | 175 |

These categories describe instructions. A local code or database task can have many real dependencies yet fall outside the requested persistent web-application producer/native-consumer scope. Reading existing state before a single write is not a newly produced-state chain. A completion announcement is not automatically a consumer. Conversely, creating a cloud file and then creating its public share is an explicit candidate chain. Exact API/native realizability and causal dependence remain untested.

## Structure and overlap

The 20 explicit tasks map to 12 analyst-coded operation families. Six are cloud file/share tasks, three create channels followed by membership/messages, and two push changes followed by merge-request creation. Multiple task instances are not independent workflow discoveries. Family codes are descriptive groupings rather than validated independence units.

Fifteen explicit tasks do not request coworker replies. They cover 10 descriptive families across GitLab, ownCloud, RocketChat and Plane. Their task IDs are saved in manifests/agentcompany-instruction-screen-summary-v1.json. The other five explicit tasks still require coworker information elsewhere in the full task; they have not been silently dropped from the frame.

All 22 conditional chains depend on coworker replies, conditional information gathering, approval, refusal, or response absence. The intermediate state may be authored by the coworker rather than controlled by the initiating API request. They therefore cannot be treated as deterministic API-producer/native-consumer comparisons without a justified environment policy. The no-paid-model constraint remains, and replaying invented replies would change task semantics.

Ambiguities remain visible. Examples include local edits followed by a required merge request with remote publication implicit, a purported Plane task pointing to the GitLab port, and cloud spreadsheet operations that may be completed locally before a single upload. No missing step was inserted to make a task eligible. The earlier Plane descriptive screen identified conditional status/cycle structure; the full dependency rule classifies that task as writes without a new prerequisite because keeping an existing issue open does not necessarily produce new state. This is a difference in the screening question, not evidence from execution.

## Decision and next evidence needed

The frame has more descriptive operation diversity than the earlier single-dependency input pools. It is adequate to justify a capability matrix across the entire 15-task no-requested-reply stratum, preserving all other strata and exclusions. It does not yet establish selector identifiability: actual dependency edges, costs, executable inputs and baseline behaviors have not been measured. Nor does diversity itself supply a new research contribution.

Do not choose the one most convenient task or build Plane solely to rescue it. The next bounded read-only step is to record, for every one of these 15 tasks, supported producer/consumer interfaces, exact service versions, reset requirements, task-asset dependencies and unresolved adaptations. Group repeated operation families before qualification, and retain task-level coverage. The previously unavailable MinIO reference remains a Plane infrastructure problem, not a task defect. Other application capabilities must be checked rather than assumed from their names or earlier deployments.

Before runtime, a contribution decision must identify what a competent information-matched API continuation would miss, or what test-selection behavior can actually differ under a fixed budget. This requires a falsifiable comparison, not a promise of defects. A qualification schedule must be frozen with exact images, environment adaptations, controls, cost caps and stopping rules. No effectiveness experiment, paid call or runtime schedule is authorized by this descriptive screen alone.

Reproduce coverage, hashes and counts using `python3 scripts/extension/summarize_agentcompany_screen_v1.py --verify`. This validates accounting and provenance, not semantic labeling accuracy, causal truth or generalization beyond this catalog. The frozen rules were informed by 18 previously read instructions (17 Plane mentions and one format example); the frame is externally authored but not an untouched holdout. All 175 instructions are now exposed. Current evidence remains insufficient for the original Q1 effectiveness claim.
