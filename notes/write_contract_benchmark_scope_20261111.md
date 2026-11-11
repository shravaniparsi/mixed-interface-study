# Write-contract benchmark scope and next evidence gate

## Decision

Continue as a bounded real-defect benchmark feasibility study. The proposed contribution is an executable collection that connects a partial-edit contract, persistent-state evidence, a historical repair, component attribution where feasible, and legitimate-write controls. This is a research hypothesis about benchmark utility, not an established novelty claim. The two completed cases are development cases. A generic preservation checker is already a competent baseline.

The common exporter now reconstructs 36 executions from the archived Tiller and Iris observations. A single implementation reports five frame alerts, zero schema alerts, zero operation-success alerts and zero requested-assignment alerts. The five alerts are manifestations of two known mechanisms. Contract assignments and derived-field exceptions are manual. No application was rerun, and no new defect was found. These are post-hoc development results, not an independent accuracy evaluation.

The export preserves per-execution source hashes, full target-row snapshots, contracts and separate project/mechanism identifiers. It cannot observe effects on other tables or services. The original application-specific reconstruction remains necessary for provenance, input validity and causal conclusions.

## Verified neighboring work

The claim-source-verification skill required a fresh-context skeptic. Two source pairings were checked: two narrowly confirmed; two stronger extrapolations rejected for lack of support. Neither confirmation establishes novelty.

- [MCPEvol-Bench, arXiv:2607.14642v1](https://arxiv.org/html/2607.14642v1), Huanxi Liu et al., July 16, 2026. The introduction states: “we extract 11 mutation operators covering the Tool, Parameter, and Description levels from observed evolution patterns.” Sections 5.2 and 6.1 evaluate agent task performance on generated server changes. Historical evolution informs construction; this does not establish a historical defect/repair corpus. Its tasks include writes and publication, so the claim that it excludes stateful tasks is rejected. The [associated repository](https://github.com/Octobrist/MCPEvol-Bench) landing page was inspected, but runnable completeness was not tested. Missing HTML appendix prompt content prevents exhaustive claims about its state oracles.
- [Description-Code Inconsistency, arXiv:2606.04769v1](https://arxiv.org/html/2606.04769v1), Yutao Shi et al., June 3, 2026. Section III states: “State mutation refers to undisclosed modifications of persistent system state.” Sections IV-B–D use static code extraction and LLM classification; V-D includes code cases with persistent effects. Generic description/side-effect inconsistency is therefore established. A claim that this paper supplies systematic runtime before/after repair validation is unsupported. A public DCIChecker artifact was not verified; an unavailable-artifact footnote about MCPDiff must not be misattributed to it.

Earlier verification also establishes that RESTestBench covers multi-step CRUD and cascades, and that cross-version REST regression testing is established. Merely adding MCP terminology or describing two bug fixes does not establish a contribution.

## Questions for the bounded continuation

1. Can the same trace format and baseline execute across distinct real partial-edit defects while preserving intended clears and documented cascades?
2. Which observation surfaces reveal each defect, and which miss it? Missing measurement is reported as unavailable, never simulated into an observed result.
3. Can component interventions distinguish a shared backend defect from adapter/backend interaction? A passing complete-payload API control alone does not prove a minimal API update would pass.
4. What engineering work and contract specification does each case require? Retrospective effort estimates are not measurements. Future actions record commands, source changes, manual contract decisions and CI time.

The next finite expansion is specified in `protocol/write-contract-corpus-expansion-v1.md`. After that cohort, assess utility against the inspected neighboring benchmarks. Do not expand indefinitely until a favorable story appears. No Q1 readiness threshold is implied by a case count.
