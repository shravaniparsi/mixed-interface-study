# Independent claim-source verification

The claim-source-verification skill was applied with a fresh-context skeptic, separate from the proposer. The skeptic independently opened the primary sources and made no repository changes. This log records the returned scope corrections; it does not introduce a new experiment or revise closed results.

| Claim bundle | Outcome | Resolution |
| --- | --- | --- |
| Measurement-injected operations can disrupt a workload and distort consistency measurements | Confirmed for the methodological claim | Rahman et al. establish this concern for storage benchmarking in 2012. Replace the broader phrase "predates web agents" with that dated, scoped statement |
| A benchmark reward oracle can change state seen by a later external scoring read while its own runner remains unaffected | Confirmed | The reported mechanism is a database reset without restoration in the studied implementation, not a cache-warming effect |
| These sources establish that evaluator pre-read cache warming changes web-agent verdicts despite identical committed business outcomes | Rejected | Neither pairing establishes that mechanism or population; they motivate a hypothesis, not its empirical confirmation or novelty |

## Supporting text

Rahman et al., section 1, Introduction, page 2: "the act of measurement disrupts the workload by injecting operations, causing a troublesome ‘observer effect’." The skeptic also checked section 2's discussion of accuracy consequences. The USENIX PDF returned HTTP 403; the independently opened text was arXiv:1211.4290v2, dated 20 November 2012. The publisher record independently confirms HotDep 2012 metadata. Do not present the two editions as byte-verified equivalents.

- Full text: https://arxiv.org/pdf/1211.4290
- Publication record: https://www.usenix.org/conference/hotdep12/workshop-program/presentation/rahman

Chen, arXiv:2610.16067v2, section 1, Contributions item 2: "resets the environment database to build a ground-truth hash and never restores it." The same passage states "the benchmark’s own runner is unaffected." Section 4.1 corroborates the external-harness failure. The benchmark's returned reward was correct; the later external state inspection encountered the reference state. Do not attribute inflated scores to the upstream runner on this evidence.

- Full text: https://arxiv.org/html/2610.16067v2

## Rejection carried forward

The rejected bundle contains two unsupported source pairings, one for each source. Rejection class: does_not_support_claim, through mechanism and population extrapolation. The former concerns intrusive storage measurement; the latter concerns oracle database mutation. The latter also includes a synthetic cache-order defect, which is not evidence of naturally occurring evaluator pre-read cache warming with preserved business outcomes. Neither source proves absence of other relevant literature.

Counts: three claim bundles reviewed; one confirmed bundle, one methodological confirmation requiring chronology narrowing, one rejected bundle containing two rejected source pairings. No paywall-blocked result remains because the author preprint was available; the publisher-PDF access limitation is retained above.

## Research decision

Generic observer effects, consistency probes, and oracle-induced state changes cannot carry a novelty claim for this project. The specific pre-read-cache hypothesis remains unvalidated, and the five archived readback records do not isolate its cause. The current evidence therefore does not justify a new cohort merely relabeled as an evaluator-effect study. A substantive contribution would still require a verified distinction, an independent sampling frame and a causal measurement design; the requirements in notes/readback_novelty_gate_20261116.md remain unmet. The original Q1 objective remains open, and no positive result or submission readiness is claimed.
