# Evidence review after the independent-input study

This is an internal scientific review of the evidence package, not a journal decision or a review of a finished manuscript. The paper-reviewer skill supplied the review structure; Nature-specific venue policies are not being applied to a software-engineering journal.

The study compared an API edit with the corresponding native edit after API creation. It selected six workflow candidates before new schema inspection and froze 44 scalar inputs before inspecting new native constraints. Three workflows reached scientific execution, covering 28 initial sampled inputs, 12 ordinary controls and four prescribed followup pairs. All 44 scientific pairs were reconstructed from retained evidence. The initial sample contained 24 clean pairs, three producer rejections and one channel difference; the difference reproduced twice and was already covered by the shared baseline.

## Assessment

The evidence is reproducible, but it does not yet establish a Q1-worthy research contribution. This judgment concerns the current scientific contribution, not the legitimacy of negative results. The study supports a narrow empirical conclusion: among the qualifying workflows and sampled inputs, native execution added no detection beyond the competent shared baseline. It does not show that native testing is unnecessary in general.

## Major points

1. **Contribution, blocking.** The proposed superiority claim has no supporting incremental detections in this study. The previous production extension also found none beyond shared checks. The verified prior-art audit already rules out claiming discovery of client/server validation gaps or downstream client harm. A publishable contribution needs a separately justified method, a substantially stronger empirical question, or an independently valuable benchmark. More repetitions of the current mechanisms would not settle this point.

2. **Agent-specific claims, blocking if retained.** These experiments replay deterministic API requests; they do not measure agent-generated actions, MCP schema use, reasoning, or an intervention on agent behavior. An agent-specific effectiveness claim requires actual tool interactions and an independently sampled task or trace corpus. Otherwise the claim must remain about cross-interface software behavior.

3. **Sampling scope, major.** Only three of six candidate workflows reached scientific execution, in previously studied applications. The scalar generator uses a small set of ordinary, empty, omitted, enum and boolean alternatives. Nested workflows, rich cross-field constraints, and a representative distribution of user intent are not covered. Neither the number of paired executions nor the 28 input variants establishes population prevalence.

4. **Qualification exclusions, major.** Custom-field renames rewrote empty metadata in both native controls, and saved-filter creation rejected the fixed empty query in all four branches. These observations remain visible, but their exclusion means the final comparison is conditional on strict ordinary-control eligibility. The paper cannot use the resulting zero incremental detections to dismiss the excluded behavior. The custom-field observation has no demonstrated harmful consequence and must not be relabelled a confirmed defect.

5. **Fixture correction and exposure, major.** Paperless storage inputs assumed ordinary actor ID 1, whereas the live actor was ID 2. The original subgroup remains unexecuted and a disclosed identity-only correction was frozen before sampled execution. This is defensible as a transparent correction, but it is not an untouched or fully blinded holdout. Count one corrected workflow, not two independent cohorts supporting the same claim.

6. **Measurement completeness, major.** Repository trust_model is absent from the API response. Its preservation was measured through the same read-only signing-settings observation in both branches. Report this shared measurement explicitly and keep its cost separate; do not describe the entire state oracle as API-only. Custom-field qualification stopped at failed raw readback, so no fresh-final native snapshot exists for those failures.

7. **Independent units, major.** The three Grocy observations concern one empty-input-to-null mechanism. The API stores null, the API description update preserves it, and native required-name validation blocks the edit. A nonnullable-string contract check already flags the state. Treat the three observations as initial plus confirmation runs, not three independent defects, and do not pool this extension with the earlier correlated variants to manufacture statistical strength.

8. **Code and data, strength with a maintenance requirement.** Pinned images, ordinary actors, matched resets, native requests, full readback, fixed repeats, failed attempts and independent reconstruction are retained publicly. The complete summary must continue to rebuild in CI, and the qualification failures and identity correction must remain part of any released dataset.

## Concrete next research gate

The current bounded study is complete. Do not add finding-driven reruns or replace excluded subjects. The next useful work is a contribution-design and prior-art check within the same area: determine whether actual MCP/API integration histories provide independently sampled cross-interface regression cases, and whether an automated compatibility intervention can be evaluated against strong existing validation methods. Establish corpus availability, a distinct falsifiable claim, and a fixed evaluation design before starting another experiment cohort. If that gate fails, recommend a research pivot rather than presenting the current package as sufficient for Q1 submission.

## Evidence locations

- `manifests/independent-input-summary-v1.json`: complete scientific funnel and outcomes.
- `manifests/independent-input-cost-v1.json`: 39 application jobs across 14 runs, 65.483 job-elapsed minutes, including four failed qualification jobs. This is not a billing invoice or total project cost.
- `manifests/independent-grocy-category-mechanism-v1.json`: three controlled comparisons of one mechanism.
- `manifests/independent-paperless-custom-exclusion-v1.json`: raw metadata transformation and unestablished harmful semantics.
- `manifests/independent-vikunja-filter-exclusion-v1.json`: fixed ordinary-query rejection.
- `protocol/independent-storage-fixture-amendment-v2.md`: identity correction and exposure disclosure.
- `notes/extension_prior_art_verification_20261110.md`: verified NoTamper, WARDroid and CRS claim boundaries; not an exhaustive novelty search.
