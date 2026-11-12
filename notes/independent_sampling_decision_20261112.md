# Independent sampling and missing-outcome decision

The preceding goal turn made progress: it completed a prospective converter pilot, preserved clean results and closed the cohort. This audit checks whether those results and the earlier independent-input cohort justify another experiment. It is a post hoc descriptive design review, not a preregistered hypothesis test.

## What the current null results cover

The independent-input cohort selected 44 inputs in six candidate workflows, executed 28, and accepted 25. Three producer rejections have known non-entry into continuation; they are not successful continuations. Sixteen selected inputs were never scientifically executed. Only three workflows qualified. The Grocy shopping-list exclusion yielded no enumerated input cases, so even the selected-input denominator does not represent all six candidates equally.

Observed incremental native-only detection is 0/25 accepted initial inputs. The 44 total scientific pair executions include controls and repeats and must not be used as an independent sample size. Nor can the converter pilot's 192 correlated synthetic pairs be added to this denominator.

The descriptive sensitivity audit assigns k hypothetical incremental detections to the 16 unexecuted selected cases, for k=0..16. Per selected input, accepted-and-incrementally-detected yield could range logically from 0/44 to 16/44 (36.36%). This is a missing-outcome range, not a confidence interval or a claim that excluded cases would yield defects. It presupposes a valid measurement procedure for those cases. It neither estimates their acceptance probability nor licenses re-running exclusions. With purposive sampling and correlated inputs, a binomial interval over all pairs would not establish application-population prevalence.

Consequently, neither a broad detector-superiority claim nor a broad equivalence claim is justified. Increasing repetitions of existing cases would not resolve workflow exclusion or sample selection.

## External sampling-frame screen

A read-only metadata screen pinned ServiceNow/webarena-verified at 6473f72db5dcefc97b5725b59e734504edc28a21. The archived task file contains 812 unique task IDs and 190 distinct template IDs. Only sites, task_id and intent_template_id were inspected for this screen. Intents, evaluator definitions and task outcomes have not been inspected in this screen. The existing project literature notes already mention WebArena, so this is not a claim of first exposure to the benchmark. Task-level prior exposure remains unproven rather than assumed absent.

Single-site counts are 182 shopping-admin tasks across 41 template IDs, 180 GitLab tasks across 41, 187 shopping tasks across 48, 106 Reddit tasks across 21, and 109 map tasks across 29. Remaining tasks span sites. These are structural identifiers, not independent defect families, confirmed writable tasks or qualified continuation workflows. No scientific subset is selected.

The official environment documentation lists optimized containers and resource sizes. Shopping Admin is listed at 2.9 GB; GitLab at 31.6 GB. These are published figures, not measured runner requirements. The small shopping-admin image makes it worth a feasibility assessment, but resource convenience must not be relabelled representative sampling. No images were downloaded or services provisioned.
Source: https://servicenow.github.io/webarena-verified/dev/environments/

WorkArena's current setup requires access to ServiceNow instances through a gated repository and approval. Its public tasks could be read, but no runtime access is established here. Do not assume that a hosted account, access approval or permitted research workload exists.
Source: https://github.com/ServiceNow/WorkArena

The authors of Beyond Browsing: API-Based Web Agents already evaluate API-only, browser-only and hybrid agents on WebArena. A benchmark-based API/browser comparison is therefore not sufficient differentiation. This is a verified project-page scope statement, not an exhaustive novelty review or reproduction of their reported performance.
Source: https://yueqis.github.io/API-Based-Agent/

## Next gate

Do not dispatch another cohort yet. Before selecting individual tasks, establish whether a post-task preserving native continuation adds empirical knowledge beyond existing hybrid-agent success and benchmark evaluator work. The exact endpoint must distinguish task completion, shared constraint satisfaction and continuation behavior. A baseline with the same contract information is mandatory.

If that contribution survives source verification, use a complete external task/template frame with deterministic eligibility decisions before outcomes, retaining non-writable tasks, missing API support, mapping failures and resource exclusions in separate denominators. Freeze a protocol before reading selected evaluator outcomes or executing tasks. Do not screen issue reports to choose likely failing tasks. Do not generate fresh variants of the closed converter fixture.

This turn adds a reproducible missing-outcome analysis and a pinned external frame, not new application evidence. The Q1 goal remains active and unmet.
