# Evaluation validity: fresh skeptic verification

Scope: checked the proposed API semantic-oracle and mutation-validity claims against six opened primary-text records. Skill: claim-source-verification. No experiments run. Search is bounded; no absence-of-literature claim follows.

## Resolution log

| Claim | Verdict | Established scope |
|---|---|---|
| Generic executable semantic API contract generation already exists | CONFIRMED | Glacier generates CRUD-based executable pre/postconditions; generic generation is not a defensible novelty claim. |
| Learned executable API assertions already exist | CONFIRMED | AGORA+ infers invariants and translates them to executable JavaScript assertions. |
| Generated semantic API assertions compared with direct prompting under shared inputs/mutants is new | REJECTED | MASTOR already reports this design for REST APIs. |
| Mutation score can include kills unrelated to explicit test assertions | CONFIRMED | Schuler–Zeller and Du et al. directly study this. |
| Assertion removal to expose mutation-score insensitivity is a new method | REJECTED | Schuler–Zeller does systematic oracle decay; Du et al. describes still earlier explicit-mutation-score subtraction work. |
| Whether API oracle rankings change under semantic-only kill attribution remains a demonstrated novel gap | PARTIAL | Worth posing as a bounded empirical question, but novelty is not established by these sources. MASTOR is a close comparator and explicitly defines assertion-based kills. |
| A generic agent-benchmark state-oracle mutation audit is new | REJECTED as a safe claim | An accessible 2026 preprint reports such an audit across three agent benchmarks; provenance caveat below. |

## Primary evidence, exact excerpts and limits

### 1. IcePick / Glacier

Ana Catarina Ribeiro, Margarida Mamede, Carla Ferreira, *Systematic API Testing Through Model Checking and Executable Contracts*, arXiv:2604.08633 (submitted 9 April 2026). Opened full HTML: https://arxiv.org/html/2604.08633

Exact excerpt, §II-B: “This module generates operation-level contracts (pre- and postconditions) from the OAS using CRUD (Create, Read, Update, Delete) semantics”.

This establishes automated semantic-contract generation, not arbitrary domain understanding. Generated contracts deliberately omit some service-specific semantics; manual predicates can add them. Evaluation §IV-D compares inferred and manually extended contracts, but the three injected Tournaments faults were all detected by both. Authors explicitly limit what that implies for domain-specific predicates. Therefore merely contrasting status checks with contracts, or asking whether manual strengthening helps, also has prior art. A follow-up needs fault families outside the inferred CRUD/HTTP scope and controlled requests.

### 2. AGORA+

Juan C. Alonso, Michael D. Ernst, Sergio Segura, Antonio Ruiz-Cortés, *Test oracle generation for REST APIs*, TOSEM (2025 per author record). Opened author-hosted abstract: https://homes.cs.washington.edu/~mernst/pubs/rest-oracle-tosem2025-abstract.html

Exact excerpt: “We also developed PostmanAssertify, which converts the invariants identified by AGORA+ into executable JavaScript assertions.”

The record establishes request/response invariant mining and executable assertions, reporting 106 invariant types. It does not establish an evaluation of kill attribution or source-mutant incidental failure confounding: its abstract describes errors seeded in API outputs. Full paper was not opened, so no detailed methodology absence is confirmed.

### 3. MASTOR

*MASTOR: A Multi-Agent Approach to Semantic Test Oracle Generation for RESTful APIs*, arXiv:2606.10465 (submitted 9 June 2026). Opened full HTML: https://arxiv.org/html/2606.10465

Exact excerpt, validity discussion: “The comparison with Direct Prompting and SATORI uses the same mutant set, test input suite, execution environment, and PostmanAssertify runtime”.

This directly overlaps a matched-input comparison. Sections 5.2–5.3 describe source mutants, status/field/multi-operation oracles, JUnit/PITest conversion, and a kill defined through assertion failure on a mutated response. It excludes uncovered mutants from the denominator and does not explicitly remove equivalent survivors. Section 8 acknowledges mutation score is a comparative proxy. Do not allege its numerator counts incidental crashes without artifact evidence: its stated definition is assertion-based. A status assertion can still react to a crash-translated HTTP error without checking the target semantic property; that is an inference requiring measurement. Table 10 has method-specific covered pools, so a shared generated pool does not itself guarantee identical effective denominators. Investigating rank stability on an identical eligible pool could be useful, but is not verified novel.

### 4. Checked coverage / oracle decay

David Schuler and Andreas Zeller, *Checked coverage: an indicator for oracle quality*, Software Testing, Verification and Reliability 23:531–551 (2013), DOI:10.1002/stvr.1497. Opened author-hosted full PDF: https://www.st.cs.uni-saarland.de/publications/files/schuler-stvr-2013.pdf

Exact excerpt, §3.5: “A test suite with no assertions still detects over 50% of the mutations detected by the original test suite”.

Sections 3.4–3.5 evaluate seven Java projects, remove 0/25/50/75/100% of assertions, and compare checked coverage, ordinary coverage and mutation score. Table IV reports 45,564 originally detected mutants versus 24,408 with checks removed. It separates explicit assertions from runtime checks and warns external-library checks remain after assertion removal. This decisively refutes generic novelty of the causal concern and the ablation. REST end-to-end behavior is outside its studied population; transfer is an empirical extension, not invention of the problem.

### 5. To Kill a Mutant

Hang Du, Vijay Krishna Palepu, James A. Jones, *To Kill a Mutant: An Empirical Study of Mutation Testing Kills*, ISSTA 2023, DOI:10.1145/3597926.3598090. Opened author-hosted full PDF: https://superhangdu.com/publications/issta-23/conference-paper.pdf

Exact excerpt, §3: “we define how a test fails due to (a) source code oracle, (b) test oracle, and (c) crash”.

The study develops kill-cause attribution across ten Java projects. The same mutant can have multiple failure causes across tests. It explains that easy kills need not be worthless: source-code defensive checks may be meaningful. Thus an API study must distinguish invalid/non-executable mutants, valid runtime-crashing mutants, and valid semantic deviations; deleting every crash kill would bake in a value judgment. Section 2.3 reviews trivial-mutant definitions; §7 discusses assertion-removal-based explicit mutation scores and their limitation when removing an assertion merely reveals a later crash. The primary method already makes generic failure taxonomy and mutation-score validity insufficient novelty.

### 6. Agent-state evaluator preprint

Shengyao Sun, *Mutation Testing of Task-Scoped State Oracles in Software-Agent Benchmarks: A Cross-Benchmark Empirical Study*, August 2026, DOI listed as 10.21203/rs.3.rs-10665114/v1. Full manuscript text opened at https://www.researchgate.net/publication/412354135_Mutation_Testing_of_Task-Scoped_State_Oracles_in_Software-Agent_Benchmarks_A_Cross-Benchmark_Empirical_Study

Exact excerpt, abstract: “We introduce a deterministic mutation-testing protocol for calibrating such task-scoped state oracles.”

The manuscript describes harmful state faults, benign transformations and matched reference evaluators on τ²-Bench, ToolSandbox and AppWorld; it reports an outcome-blinded mutation-validity audit, applicability exclusions, and comparison of evaluator rules on the same synthetic states. This overlaps a broad state-oracle calibration pivot. It is a preprint, not confirmed peer reviewed. The DOI target redirected to Research Square but retrieval failed; the visible manuscript supplies substantive evidence, while independent publisher/version provenance remains BLOCKED. No artifact or numerical replication was performed.

## Distinct question worth testing, without claiming novelty

For a declared set of REST APIs and fixed valid request sequences, does the ranking of status/schema, direct-natural-language generated, and contract-based assertions change when kill credit requires an independently specified target semantic violation rather than any failing check?

The meaningful contribution would be an API-specific result and reproducible attribution corpus: link server mutation, HTTP manifestation, failed check and intended requirement; distinguish server failures translated to status codes, response-parser failures, prerequisite failure in stateful sequences, and genuine property violations. Hold mutant eligibility and traces fixed, report both total fault detection and incremental semantic detection, and include benign variations to measure false rejection. Retain a separate no-assertion arm but cite it as established methodology. Include real API bugs or manually validated fault classes to test whether any ranking changes matter outside the mutation operators. These are design recommendations, not confirmed gaps.

## Rejections and remaining work

Rejected claim classes: three overbroad novelty claims (matched API comparison; assertion-removal method; generic agent-state audit). Generic incidental-kill novelty is also ruled out by the confirmed historical claim. Do not reuse papers as evidence that all API semantic-oracle evaluations are confounded; that would exceed their populations and, for MASTOR, conflict with its stated kill definition.

Counts: six substantive records opened; seven claim pairings evaluated: three CONFIRMED, three REJECTED, one PARTIAL. One supplementary provenance verification BLOCKED. No source rejected for nonexistence; rejection concerns claim scope/novelty. Still needed: inspect MASTOR runnable evaluation to establish actual exception handling and eligible pools; inspect AGORA+ full text; search API-specific kill-attribution and SATORI primary work before asserting a literature gap.
