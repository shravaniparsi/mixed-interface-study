# RealWorld execution integrity validation v1

This prospective engineering regression uses only previously examined cases. It adds no independent experimental sample and does not complete the primary freeze.

The selection manifest fixes 22 branches: six generated branches (four route controls and two known body-empty rejections) followed by sixteen legacy branches (ten positives and six known rejections). Each executes once from its reset fixture. Exact IDs, order and expected HTTP status are in `manifests/realworld-integrity-controls-v1.json`. No Quartz boundary case is included.

Before dispatch, the validator archives executing scripts, helper, registries, protocol and workflow bytes, with SHA-256 hashes and environment sidecars. Generated execution has a 180-second outer timeout; legacy execution has 240 seconds; each has 20 seconds of termination grace. No automatic retry, resumption, partial replacement or merging across attempts is permitted. Failed attempts remain evidence.

Every positive must pass ordinary business checks, complete response capture, exact submitted method/path/payload comparison, and the applicable returned-resource or settings-form guards. Command arrays retain their exact order. Binding and snapshot tag membership uses set semantics; existing legacy business predicates retain their historical tag comparison. Native comment deletion is qualified only for the explicit singleton-comment fixture, one delete control, and the observed returned-id DELETE target.

Each known rejection must return 422, execute no continuation, and have readable, equal before/after API-visible snapshots. Snapshots include public current-user fields, the complete own-article list, global tag membership and comments on every listed article. Article/comment fields and timestamps are retained; authentication tokens are excluded. Missing, partial, duplicate or failed probes cannot establish unchanged state. This is an observable-state comparison, not a claim of database atomicity. Changed, unreadable and unobserved states remain distinct.

Postflight independently rebuilds snapshots from trace-backed probes, recomputes guard comparisons and resource bindings, qualifies archived sources, and requires every selected branch. Partial successes do not qualify the run. This validation neither estimates defect prevalence nor measures selector effectiveness. PetClinic guards, legacy owned-process cleanup qualification, broader pairing and the remaining freeze gates are separate outstanding work.
