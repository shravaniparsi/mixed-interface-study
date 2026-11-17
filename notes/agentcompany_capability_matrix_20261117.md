# Full-stratum capability matrix

The previous goal turn completed the frozen-rule screen of all 175 task instructions. This turn examined service configuration and version-matched interface source for all 15 explicit-chain tasks without requested coworker replies, covering all 10 descriptive families. Every task remains in manifests/agentcompany-capability-matrix-v1.json, including unresolved requirements. No tasks were selected based on failures, no graders were inspected, and no applications or paid research model calls ran.

The pinned benchmark source declares GitLab CE 17.5.1-ce.0, an ownCloud 10.0.10 base and RocketChat 5.3.0. The ownCloud image also copies custom apps/data, and Compose includes Collabora 24.04.9.2.1. These declarations do not establish the versions actually packaged in mutable image tags. Upstream sources were resolved to GitLab e8dca57316730f48a89e1914c224c5d9bac42bc3, ownCloud 097d4d22e0cf3341c4923e26453efb32ddedfb24 and RocketChat eb122008e0d35b01ae9212250d4f68f58fa89c54. Their correspondence to benchmark image contents is unverified. Previous GitLab 15.7.5 controls cannot qualify this different deployment.

## Interface evidence

| Family group | Source-supported operations | Remaining qualification questions |
| --- | --- | --- |
| ownCloud file/share | WebDAV file put, link-share creation, browser share dialog | Packaged apps/settings, browser upload, real task artifacts and accessible share |
| ownCloud file/chat publication | File put and RocketChat message endpoint | Full slides task reads all four applications, including unavailable Plane stack |
| ownCloud memo derivation | File persistence and configured Collabora service | Actual ODT editing/template derivation and persisted-state consumption, not replacement by arbitrary uploads |
| RocketChat channels/membership/messages | Create, invite, kick and message endpoints; browser creation and membership actions | Permissions, identities, browser composer, message/mention persistence and reset |
| RocketChat roles/bio | Moderator/leader endpoints; browser role actions; user-update bio schema and admin bio form | Acting-user permissions and exact intermediate state, especially editing another user's bio |
| GitLab milestone/assignment | Version-matched milestone and issue APIs and browser instructions | Exact populated milestone/issues, identity, permissions and matched state |
| GitLab push/merge request | Commit and MR APIs; browser MR documentation | Requested Git push must not silently become an API commit; exact code task and producer adaptation remain unresolved |
| Plane project/members/issues | Previously archived partial route evidence | MinIO availability, packaged-source equivalence, restoration, forms and assignment semantics |

RocketChat browser creation explicitly calls the channels.create REST endpoint. Browser role actions call corresponding role endpoints, and its admin bio form submits to users.update. Consequently API baselines should receive the same operation knowledge and permissions. Source sharing does not prove equivalent inputs, frontend constraints, observable outcomes or costs; it also does not prove a validation gap. Inputs have not been selected from a discovered validation failure.

## Task and reset fidelity

The matrix records source artifacts and full-instruction service mentions separately from the candidate chain's two endpoints. This prevents hiding dependencies: the slides task requires information from all four services, while the group-channel task uses an ownCloud spreadsheet whose filename varies between two spellings in its instruction. Neither task may be replaced by arbitrary content merely to exercise an endpoint. The two Sotopia tasks require actual agent implementations and branch publication; a placeholder patch would not complete either task.

Benchmark Makefile source describes GitLab and ownCloud resets by container recreation, RocketChat restoration using mongorestore --drop and a fixture dump, and Plane stop/restore behavior through its separate stack. Those are source-declared operations, not measured reset guarantees. RocketChat Compose uses the bitnamilegacy MongoDB namespace and includes separate NPC infrastructure. Excluding NPC execution for no-reply tasks would need a recorded isolation plan and evidence that required state/permissions remain available.

Both the configured MinIO Docker Hub path and the tested upstream Quay path remain unavailable through the previously tested anonymous access methods. No image substitute was introduced. The remaining service image digests, full fixture availability, resource use and runtime state are not yet qualified. A missing guessed RocketChat .tsx path was resolved through the directory listing to the actual .js form; the navigation miss is retained and is not an application capability failure.

## Contribution decision

The full-stratum matrix supports further bounded feasibility work, but not an effectiveness claim or immediate scientific dispatch. The concrete next step is resolve the remaining exact image references and task assets, then decide whether a prospective ordinary-control schedule can preserve full task semantics within the existing free-compute bound. Any adaptation must be explicit before outcomes. No new paid services are needed for the present source checks.

Before scientific execution, the protocol still needs a falsifiable method comparison with competent, information-matched baselines and measurable differences in candidate selection or oracle observations. Merely knowing more API routes, finding source-level operation support or assembling more tasks does not supply that contribution. No causal evidence, defect count, agent success rate or Q1 readiness is added by this matrix.

Reproduce provenance and complete-stratum coverage with `python3 scripts/extension/verify_agentcompany_capability_v1.py`. It checks all 15 task records, ten family entries, archived bytes and literal evidence anchors. It does not certify semantic interpretation, source/image equivalence, permissions, actual browser interactions or task completion. All raw sources and licenses are retained in results/agentcompany-service-capability-v1 and results/agentcompany-interface-source-v1.
