# Hosted execution, 7 November 2026 UTC

The private repository is [shravaniparsi/mixed-interface-study](https://github.com/shravaniparsi/mixed-interface-study). GitHub Actions now prepares the applications from their recorded upstream versions and runs the research harness on Ubuntu 24.04. The validated application-code commit is `f1dfdc325e823f04140821be51a4379082e6babf`.

| Hosted run | Result | Scope |
| --- | --- | --- |
| [Unit checks, 42351280533](https://github.com/shravaniparsi/mixed-interface-study/actions/runs/42351280533) | Passed | 75 Python harness, six bootstrap/context and eight Node adapter tests |
| [Quartz controls, 42351328794](https://github.com/shravaniparsi/mixed-interface-study/actions/runs/42351328794) | Passed | One stored-job workflow across UI/UI, API/UI, UI/API and API/API |
| [RealWorld integration, 42351333552](https://github.com/shravaniparsi/mixed-interface-study/actions/runs/42351333552) | Completed | 18 validations, eight calibration controls and nine budgeted sessions |

Quartz's four controls use the same admin actor and have equal complete initial and final states across routes. All 62 recorded checks pass. Backend termination, released application ports and two empty browser-process scans are recorded for every case. No Quartz boundary candidate has run. Local adapter interruption probes are separate from these hosted ordinary controls.

RealWorld's validation outcomes are ten successful workflows, six HTTP 422 prefix rejections and two HTTP 500 prefix server errors. These outcomes agree with the existing development integration pool; successful pipeline execution does not mean every application input was accepted. Its fresh calibration yields a 28.960350857-second session budget. Across nine sessions, 105 workers started, 96 completed in budget and nine were interrupted. All 131 reset records match the fixture hash, and all 131 parent browser-cleanup records confirm cleanup. Four interrupted workers had launched browsers; five stopped before launch. No late feedback was credited. The downloaded source, input and observation hashes were recomputed using `scripts/summarize_runtime_integration.py`; all checks passed. There is no separate hosted final fresh-control health check beyond the recorded cleanup and within-run resets.

Linux timings are a separate environment stratum from the earlier Mac integration, which used a 20.696-second budget. These runs establish execution, binding and accounting feasibility. They do not estimate selector effectiveness or fault prevalence, add independent applications to the sample, or establish a Q1-level contribution. Native upstream application unit suites were not repeated in these CI runs.

## Reproduction and retention

Pushes and pull requests run the unit workflow. Application checks are manual, with `quartz-controls` and `realworld-integration` choices, one application job at a time. Unit jobs have a five-minute ceiling and application jobs a twenty-minute ceiling. See [the CI runbook](ci_reproduction.txt) and [portability amendment](../protocol/ci-portability-v1.md).

Actions and Chromium are pinned; subject commits, Quartz dependency hashes and Python package versions are recorded. Node 20, Python 3.12 and Ubuntu image labels may resolve newer builds. The Python requirements pin versions but do not require wheel/sdist hashes. Each run records resolved versions and installation metadata; the primary experiment still needs its environment freeze.

[GitHub execution metadata](../manifests/github-execution.json) records commit IDs, job times, artifact sizes/digests and evidence paths. Reviewed compact summaries are tracked in `results/hosted-validation-20261107/`. Complete downloaded CI artifacts are retained locally in `results/ci-runs/`; historical raw case evidence also remains in its original local directories. Those full raw directories are excluded from Git. The GitHub artifacts expire after seven days, on 14 November UTC for these runs, so the repository alone is not a full raw-data backup. A durable research-data archive remains a pre-submission requirement.

The first workflow versions were rejected before application jobs started because `runner.temp` was referenced in unsupported job-level environment expressions. Runs 42350924553 and 42350925611 preserve those failures. The correction initializes paths in shell steps and exports them through `GITHUB_ENV`; a regression check covers this context restriction.

## Storage and cost

After hosted execution was verified, only the two task-owned frontend `node_modules` directories were removed. Observed free space increased by 736,112,640 bytes, about 736 MB, to about 1.19 GB at measurement time. Application sources, built assets, lockfiles and experimental evidence were preserved. Local frontend rebuilds now require restoring dependencies. [Cleanup record](../manifests/local-storage-cleanup-20261107.json).

No paid model API calls or larger runners were used. GitHub account allowance and actual charges have not been inspected, so hosted execution is not recorded as confirmed zero-cost usage. Jobs are bounded and application runs require manual dispatch.

The next scientific milestone is completing the multiworkflow eligibility and constraint ledger, then freezing the paired-oracle corpus before inspecting the 40 unexecuted Quartz boundary candidates.
