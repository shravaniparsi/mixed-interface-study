# Public workplace benchmark feasibility

Decision: do not launch the full The Agent Company benchmark. Its public instructions offer an external workflow catalog, but this screen does not establish an eligible experimental cohort, a new method, or a Q1 contribution. A bounded capability review of the project-membership-issue chain is justified before considering execution.

The official repository was pinned at 98b68ef82a47690c316f42fddb05baafaab56851. The archive contains all 175 task instruction files, the image catalog, setup/evaluation documents and MIT license: 179 source files totaling 131,643 bytes. The catalog and instruction directories match exactly, including the example task. Each instruction's Git blob ID matches the repository tree; all archived source files have SHA-256 hashes. The archive does not contain graders, checkpoint rubrics, solutions, trajectories or observed task outcomes. No applications, agents or model calls ran.

Exposure: all instructions are now available to this study's inventory tooling. The analyst read all 17 instructions with a literal Plane name or service-port reference, plus admin-arrange-meeting-rooms as a format example. This is not an untouched holdout. The source catalog was independently authored, but the proposed application focus and instruction coding are analyst decisions. No previous Agent Company mention was found by the current text search of this project's notes, protocol and manifests; that is not proof of no historical exposure outside those files.

## Mechanical inventory

Literal service-name/port matches occur in 71 GitLab, 69 ownCloud, 17 Plane and 79 RocketChat instructions. Categories overlap. These are text counts, not counts of eligible workflows, required services, API support or deterministic grading. For example, an onboarding presentation mentions every service without creating a Plane object. The scanner's exact expressions and per-task labels are in manifests/agentcompany-instruction-inventory-v1.json.

## Plane instruction review

The single-analyst descriptive coding covers all 17 matching instructions in manifests/agentcompany-plane-instruction-screen-v1.json. It is not independent adjudication or a final inclusion rule.

| Instruction structure | Tasks |
| --- | ---: |
| Project creation, membership, dependent issue assignment | 1 |
| Conditional issue status and cycle update | 1 |
| Requires a coworker's response | 3 |
| Output or state update followed by chat publication | 3 |
| Cross-system reading/computation followed by writing | 4 |
| Creation, deletion or existing-issue update | 3 |
| Read-only endpoint identification | 1 |
| Application name conflicts with URL | 1 |

pm-assign-issues explicitly requests a new Backend Development project, three named members, and three assigned issues. Unlike the previous single-edge input pools, its stated operations span project-to-membership and membership-to-assignment relationships. It remains one workflow, not three independent workflows or defects. The instructions do not prove that these relations are enforceable API dependencies, that equivalent native producers exist, or that any selector would outperform a competent baseline.

The ambiguous close-all task names Plane but supplies the GitLab port. Do not silently repair the instruction. Several tasks require coworker responses; chat mentions alone do not prove that a paid NPC is required. Other tasks publish messages without requesting replies. These differences must survive any later eligibility coding.

## Resource and scientific gates

The pinned setup documentation specifies at least 30 GB free storage and launches GitLab, Plane, ownCloud and RocketChat. Evaluation documentation describes environment model use for coworkers and some graders. The full published evaluation is therefore not established as a no-paid-model, bounded runner workload. No paid execution or large download has been scheduled. A service-isolated study would be an adapted task study, not a reproduction of the full leaderboard evaluation.

Before any new scientific schedule: establish the pinned Plane service version and reset/isolation requirements; verify documented API and native capabilities for the exact operations; define an outcome-independent eligibility rule for the full candidate frame; establish sufficient workflow and dependency diversity; specify information-matched baselines, invariant contracts and measurement boundaries; and justify the contribution against prior work. Do not use one promising-looking task as a prevalence sample or append perturbations until a failure appears. No runtime findings or fault reports should influence frame selection. Any ordinary capability trial must have a separately bounded, prospectively recorded schedule.

Next concrete step: inspect only infrastructure and documented interface capabilities for the project-membership-assignment chain. If isolation or equivalent operations fail, record the exclusion. If they succeed, assess the entire intended candidate frame before enrollment. A successful capability check alone does not authorize relabeling the prior selector study or restarting closed cohorts.

Reproduce the inventory with `python3 scripts/extension/inventory_agentcompany_v1.py --verify`. This checks archived bytes, task/catalog agreement and screen coverage; it does not validate the analyst's semantic labels or application behavior.

Primary source: https://github.com/TheAgentCompany/TheAgentCompany/tree/98b68ef82a47690c316f42fddb05baafaab56851. The pinned docs/SETUP.md and docs/EVALUATION.md support the resource findings; archived task instructions support the descriptive coding. All previous scientific denominators and conclusions remain unchanged.

Infrastructure follow-up completed: notes/agentcompany_plane_infrastructure_20261116.md records a moving dependency branch, tagged images, isolated-stack source structure and partial route evidence. Runtime qualification remains unperformed; no scientific enrollment or new application experiment follows from this review alone.
