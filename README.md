# Mixed-interface workflow testing

## Current status, 11 November 2026

The independently selected API-input study is complete. Its finite schedule contains **44 scientific paired executions** across three qualified workflows in previously exposed applications: 28 initial sampled inputs, 12 initial valid controls and four followup pairs. The initial sampled inputs yielded 24 clean pairs, three producer rejections and one channel difference covered by the shared baseline. There were **zero additional native-only detections and zero confirmed natural defects**. Three of the six candidate workflows were excluded before scientific execution; a Paperless owner-fixture correction is disclosed. This is not untouched-application validation.

[Independent-input summary](manifests/independent-input-summary-v1.json) · [Evidence review](notes/independent_input_evidence_review_20261111.md)

Separate historical calibrations now reproduce one known Tiller mechanism in 12 executions and one known Iris mechanism in 24 executions. The Iris four-cell intervention separates adapter and backend remedies and retains intended-clear controls. These outcome-selected development cases establish replay feasibility and causal evidence, not new-defect discovery or independent detector efficacy. **A Q1-level contribution remains unestablished.** Their counts are not pooled with the independent-input study.

[Tiller calibration](notes/write_preservation_calibration_results_20261111.md) · [Iris component results](notes/iris_write_preservation_results_20261111.md) · [Prior-art scope verification](notes/write_preservation_prior_art_verification_20261111.md)

The [shared write-frame export](manifests/write-frame-development-v1.json) reconstructs all 36 historical executions with one baseline implementation. Contracts remain manual; this is development reconstruction, not independent efficacy. The [bounded next cohort](protocol/write-contract-corpus-expansion-v1.md) fixes four additional historical leads and stopping rules; the [contribution review](notes/write_contract_benchmark_scope_20261111.md) records the remaining benchmark-utility question.

Expansion update: Superset has an ambiguous pre-repair contract and was not dispatched. Vikunja’s bounded calibration exhausted its correction allowance with bulk calls authorization-denied; it adds no scientific bulk evidence. [Retained qualification results](notes/vikunja_bulk_qualification_results_20261111.md). Fast Dash now has eight observed executions: six controls qualify, while the pinned repair’s parent-change case exposes a missing-state/readback/invocation discrepancy. It is not counted as a fully qualified repair. [Cascade results](notes/fastdash_cascade_results_20261111.md). TestPlanIt completed its two allowed attempts but failed in study harness code before scientific execution. [Qualification record](notes/testplanit_tags_qualification_20261111.md). The six-lead cohort is now closed; its [contribution assessment](notes/write_contract_cohort_review_20261111.md) does not establish Q1 readiness. No application experiment is running.

The [portable contract replay](notes/write_contract_replay_20261111.md) now covers 36 Tiller/Iris records plus eight Fast Dash observations with one checker. It reproduces seven previously identified violating observations using manual contracts; no new application executions or automatic-inference advantage are claimed.

The [contract-information ablation](notes/contract_information_ablation_20261111.md) shows that allowing derived changes is insufficient: their expected values matter. Continuation-agreement checks add zero detections over the complete manual transition contract on these traces. [Verified prior-art scope](notes/contract_inference_prior_art_20261111.md).

The original registered experiments and selected repetitions are complete. The corrected Quartz collection covers 22 cases: 14 clean observations, five matching rejections, three unresolved policy cases, and zero eligible check mismatches. Eight original Quartz measurements remain invalid. One original eligible UI-only PetClinic check mismatch remains, observed in three repetitions; repeats are not independent defects.

[Completed results and evidence](notes/registered_experiments_complete_20261110.md) · [Machine-readable completion](manifests/experiment-completion-v3.json)

The repository is now public. Heavy work uses standard public GitHub runners. The cash ceiling remains $100. No paid model calls are requested for the new extension.

The production extension is complete across linkding, Paperless-ngx, Grocy, Memos, Vikunja and Gitea. It covers 16 ordinary workflows, with boundary candidates in 15; Gitea's field-local issue-body editor contributes controls but no applicable preserved-field constraint. The finite schedule contains **358 paired executions**: 150 initial boundary variants, 64 initial valid controls, and 144 followup pairs. All ten result files reconstruct exactly from archived raw evidence. Of 72 scheduled boundary repeats, 71 have qualified linked controls and match their initial outcomes; one Memos repeat remains unqualified after its control failed.

| Application | Initial boundary variants | Producer rejected | Both clean | Channel differences | Documented normalization |
| --- | ---: | ---: | ---: | ---: | ---: |
| linkding | 24 | 14 | 10 | 0 | 0 |
| Paperless-ngx | 36 | 15 | 21 | 0 | 0 |
| Grocy | 28 | 6 | 9 | 13 | 0 |
| Memos | 16 | 4 | 8 | 4 | 0 |
| Vikunja | 27 | 12 | 12 | 1 | 2 |
| Gitea | 19 | 7 | 4 | 8 | 0 |
| Total | 150 | 58 | 64 | 26 | 2 |

All 26 initial channel differences are covered by shared constraint/contract/reference checks: **zero additional native-only detection signals** in this prospective cohort. A successful API write and full API edit can coexist with a blocked native edit or a changed preserved field. Input-only counterfactual packets substantiate those behaviors; they do not establish new defects. Variants and repeats are correlated. The separate nine-pair Grocy energy investigation remains exploratory and is excluded from this table.

[Summary](manifests/production-extension-summary-v1.json) · [Complete raw-evidence reconstruction](manifests/production-extension-reverification-v1.json) · [Finite compute accounting](manifests/production-extension-cost-v1.json) · [Protocol](protocol/production-extension-v1.md) · [Verified prior-art limits](notes/extension_prior_art_verification_20261110.md)

The finite runs used 91 jobs and 183.45 job-elapsed runner minutes, including job setup/upload but excluding queue time and earlier qualification work. No paid model calls were made. This is compute accounting, not a billing statement.

**Contribution assessment: no-go for submission claiming a new, broadly superior detector.** The dataset supports a reproducible empirical account of interface-specific continuation failures. It does not yet establish the distinct contribution needed for a strong Q1 submission. Client/server validation gaps and downstream client harm have prior art. Moreover, deriving candidates from native constraints favors a shared constraint baseline by construction; the zero incremental yield must not be generalized to all possible API-created states. Eight Memos preference variants trigger shared membership checks yet allow the prescribed edit, so a constraint alert alone is not proof of task failure. No LLM-agent performance, preventive guard efficacy, or population prevalence was measured.

The next defensible research question is whether native continuation provides useful outcome confirmation on inputs selected independently of its own constraints. That requires a separate prospective sampling protocol, previously unexamined workflows, a frozen baseline and explicit valid-write costs before new outcomes are viewed. Additional repetitions of this completed pool would not resolve that question. This recommendation is not an authorization to relabel the existing pool as held-out evidence or to claim Q1 readiness.

To recheck the finite cohort without overwriting proof files: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts/extension python3 -c 'from verify_production_extension_v1 import build; print(build()["total_pairs"])'`.

Reconstruct the completed package with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 scripts/build_experiment_completion_v3.py --verify`.

## Historical development notes

The following text describes earlier stages, including superseded readiness and repository-visibility statements. Use the current summary and dated completion manifest above for present status.


Research prototype and executed feasibility pilot, 6 November 2026 Pacific time (7 November UTC).

Public source repository: [shravaniparsi/mixed-interface-study](https://github.com/shravaniparsi/mixed-interface-study). Git includes reviewed compact summaries; complete historical case evidence remains in the original workspace. [Evidence coverage and restoration prerequisites](results/README.md). Hosted runs follow the separate [CI portability amendment](protocol/ci-portability-v1.md).

The question is whether substituting API operations for native UI operations preserves the ability to complete a web workflow, and whether tests that track interface-specific dependencies find failures efficiently. The proposed contribution remains under evaluation.

## Historical development findings

The expanded source-guided batch covers **7 workflow templates, 44 case variants and 86 independently reset replay branches** across the two applications. It reproduces one known PetClinic UI compatibility blocker and one RealWorld returned-identifier defect. The PetClinic API edit passes while the corresponding UI edit is disabled; the RealWorld failure is detected by both API and UI continuations. Diagnostic repeats and controls are stored separately.

[Read the findings and their limits](notes/development_findings.md) · [Recomputed counts](results/development-batch-v2/summary.json) · [Candidate table](results/development-batch-v2/candidates.csv)

These are exploratory development results. Server errors, unresolved whitespace policies and shared preflight failures are kept separate from the two reproduced findings. No selector-effectiveness or agent experiment has run, and no previously unknown fault has been established.

## Historical runtime integration and third application

The 18-case generated RealWorld pool now executes through a measured-budget controller. A complete integration batch includes 18 validations, eight cost-calibration controls and nine sessions on a common 20.696-second budget. Across sessions, 105 workers started, 96 completed in budget and nine were interrupted; no late feedback was credited. Earlier incomplete attempts are retained. This is execution/accounting verification, not selector-effectiveness evidence.

Quartz Manager's generated-case adapter now passes one stored-job workflow on all four UI/API routes locally and on GitHub Actions, with equal complete initial and final state hashes within each run. Its 44-case v2 pool contains four route controls and 40 boundary candidates; the boundary candidates remain unexecuted and the primary corpus freeze is pending. Local interruption probes also verified cleanup before and after browser launch.

Hosted CI passed 75 Python harness tests, six CI bootstrap/context tests and eight Node adapter tests. A fresh Linux RealWorld integration completed 18 validations, eight calibration controls and nine sessions on its own 28.960-second budget. All 131 resets and browser cleanup records were confirmed. Linux and Mac timings remain separate. [Cloud execution and evidence](notes/cloud_execution.md) · [CI run provenance](manifests/github-execution.json)

[Detailed integration report](notes/runtime_integration.md) · [Quartz control](manifests/quartz-transfer-control.json) · [Next evaluation gates](protocol/multiworkflow-freeze-gates-v1.md)

## Initial positive-control pilot

| Subject | Independent workflow templates | Routes | Executions in accepted pilot | Outcome |
| --- | ---: | --- | ---: | --- |
| RealWorld Django Ninja + Vue | 1: create article, edit body, read | UI/UI, API/UI, UI/API, API/API | 8: two repetitions per route | All passed; expected final business state equal |
| Spring PetClinic REST + Angular | 1: create owner, edit address, read | UI/UI, API/UI | 2: one repetition per route | Both passed; initial state, creation payload and final state equal |

These initial runs used two workflow templates, not ten independent samples. They established execution feasibility before the boundary batch above. They are not included in its 86-branch count.

Native application suites previously passed locally: RealWorld backend **92**, frontend **58**; PetClinic backend **248**, frontend **88**. The research harness suite passed **75 tests**, covering selectors, registries, generated-pool consistency, runtime accounting and owned-process cleanup. These counts describe separate suites and are not study sample sizes. The hosted jobs did not rerun those native application unit suites. No paid model API calls were made; GitHub's actual charge and remaining included allowance have not been checked.

- [RealWorld accepted pilot](results/realworld-20261107T021931Z/summary.json)
- [PetClinic accepted pilot](results/petclinic-owner-pilot/paired-summary.json)
- [Protocol amendment and next experiments](protocol/pilot-v0.2.md)
- [Evidence and interpretation](notes/result_summary.md)
- [Machine-readable study status](manifests/study-status.json)

## What is implemented

`src/mixed_interface/selection.py` provides seeded random, generic dependency-coverage, and interface-specific dependency-coverage selectors over the same finite candidate pool. Coverage is credited only after explicit execution feedback. The code rejects predicted coverage being counted merely because a candidate was selected or an operation reached. It is not a reproduction of RESTler. The new immutable registry generates bounded route and API-payload variants with explicit requirement provenance and interface exclusions. An 18-case RealWorld pool matches the registered mutation inputs. The new runtime controller and RealWorld adapter connect generated operations to returned resource/state bindings and observed dependency feedback. They enforce external-process deadlines, confirm owned-process cleanup and record actual elapsed costs. The older exploratory boundary batches remain separately registered executions.

`scripts/run_realworld_pilot.py` creates a synthetic fixture in a new task-owned SQLite database, stops the backend before snapshotting and restoring, verifies restoration hashes, and launches a fresh browser for each route. It saves exact runner sources and build fingerprints. The final check includes a fresh native UI read after persistence. Fixture hashes are equal within a run; independently created fixtures need not have identical bytes across runs.

PetClinic scripts, operation mapping and setup instructions are under `scripts/`, `manifests/petclinic-owner-workflow.json`, and `notes/petclinic_ui_setup.txt`. Its H2 reset was verified at the complete owner-graph observation, not by a full database byte hash. Both routes used the native anonymous actor because security was disabled in this configuration.

## Reproduce the local controls

Run selector checks from this directory with Python 3.9 or newer:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
```

For RealWorld, first prepare the pinned backend, Python environment and built frontend described in [setup instructions](notes/realworld_setup.txt). With Playwright available and Chrome installed, use:

```sh
PLAYWRIGHT_MODULE_PATH=/absolute/path/to/node_modules/playwright \
CHROME_EXECUTABLE=/absolute/path/to/chrome \
python3 scripts/run_realworld_pilot.py \
  --subject /absolute/path/to/realworld-django-ninja \
  --python /absolute/path/to/venv/bin/python \
  --node /absolute/path/to/node20 \
  --runtime-root /absolute/path/to/task-runtime \
  --repetitions 2
```

Ports 18765 and 18766 must be free. The frontend must have been built with `VITE_API_HOST=http://127.0.0.1:18765`. The runner binds the backend and frontend to loopback, creates synthetic data, and stops its servers on completion. Browser requests to external resources are blocked, so this pilot makes no visual-layout or external-integration claim. Upstream Cypress end-to-end tests were not run.

RealWorld substitutes `psycopg2-binary==2.9.10` for the upstream `psycopg2==2.9.6` dependency because the application imports that module even with SQLite. Application source was unchanged; outcomes apply to this SQLite configuration. Frontend native tests ran in UTC. Earlier setup attempts, including a local-timezone test failure, remain in the logs.

## Preserved unsuccessful attempt

[The first RealWorld run](results/realworld-20261107T021733Z/summary.json) passed six of eight executions. UI/API failed its final DOM check twice despite successful persistence. The browser was already on the article hash route, and navigation to the same hash issued no new article GET. The revised runner reloads and observes a fresh article GET for every route. Original traces and exact runner sources are retained. This change tests fresh-read compatibility; it does not establish automatic synchronization of an open tab. See [the adjudication record](notes/realworld_oracle_correction.md).

## Next work

The eight-workflow eligibility/constraint ledger and declared pair index are complete. They register 42 examined development pairs, nine generated engineering pairs, 22 Quartz pairs and two unpaired native controls. Overlapping catalogs remain separate; these are not independent sample counts. The primary evaluation freeze is still incomplete.

Source-qualified reducers now separate recorded components for RealWorld, PetClinic and Quartz, including shared API readback and supplementary UI verification. Retrospective extraction qualifies 140 of 144 archived records; four RealWorld context-close capture errors remain incomplete. The Quartz controls-only paired campaign passed on the hosted runner: two valid pairs, four fresh JVMs, matching actors/states/payloads and confirmed cleanup. No Quartz boundary cases ran. The subsequent RealWorld capture repair passed fourteen hosted ordinary controls with ninety matched native request/response records and zero capture errors; its hosted unit suite passed all 188 tests. Next, strengthen executing-adapter guards and extend paired replay before the primary freeze. [Capture repair](notes/realworld_capture_repair.md). [Extraction report](notes/oracle_extraction.md) · [Paired-control evidence](manifests/quartz-paired-control-validation.json) · [Readiness report](notes/evaluation_readiness.md) · [Detailed ledger](manifests/multiworkflow-eligibility-v1.json) · [Prospective analysis](protocol/paired-oracle-analysis-v1.md) · [Preparation snapshot](manifests/evaluation-preparation-v1.json)

Compare native UI continuation with competent API-semantic follow-up checks first. A larger pool with multiple dependency structures is required for primary selector-effectiveness evaluation. Historical, injected and previously examined faults remain separate. Magento remains an unevaluated candidate; Quartz control feasibility is established.

The earlier manuscript and submission-plan DOCX files are planning drafts. The v0.2 protocol amendment in this repository records current experimental decisions. Current development results are in notes/development_findings.md. A Q1-level method contribution remains to be established.
