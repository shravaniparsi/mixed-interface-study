# Readback measurement: preliminary novelty gate

This is a scoped primary-source review following the archived README diagnostic. It is not a systematic literature review or proof that a narrower topic is novel. No experiments, model calls, or application writes were performed for this review. The closed cohort is unchanged.

## Established neighboring methods

| Primary source and inspected material | Supported scope | Implication for a new claim |
| --- | --- | --- |
| Freitas et al., Characterizing the Consistency of Online Services, sections III–IV | Defines consistency anomalies for service APIs and uses read/write probes; discusses clock synchronization when measuring divergence windows | Testing API read-after-write behavior or timing divergence is not new merely because an agent can call the API |
| Jepsen 0.3.11 checker documentation, set-full | Tracks stale, lost, never-read and stable observations, including first-read and stability latency; validity depends on the expected model | Retaining observation histories and distinguishing delay from loss is established methodology |
| WAREX, arXiv:2510.03285v1, section 3 | Uses a proxy to inject web failures into existing agent benchmarks and evaluates reliability and efficiency | A generic web-agent transient-failure or delay benchmark is insufficient differentiation |

Sources:
- https://asc.di.fct.unl.pt/~nmp/pubs/dsn-2016.pdf
- https://jepsen-io.github.io/jepsen/jepsen.checker.html#set-full
- https://arxiv.org/html/2510.03285v1#S3

The WAREX methods inspected include network, server and JavaScript failures. That is not evidence that its authors tested our precise cache mechanism, and absence of that mechanism from this scoped inspection does not establish a novel gap. The earlier project reviews of REST oracles, GUI/API testing and benchmark evaluator integrity remain relevant; this note does not supersede them.

## Decision

Reject the broad proposed contribution "a polling-based consistency-aware oracle for web agents" as currently insufficiently differentiated. Do not allocate a new application cohort on that premise. The README diagnostic identifies a plausible measurement mechanism in one exposed system, not general prevalence or causally established evaluation bias.

A narrower candidate question is whether an evaluator's own pre-write read changes its later verdict, despite an identical committed business outcome, and whether that effect changes comparisons between interface paths. This is an explicit hypothesis for literature and design review, not a claim of priority. General observer effects, caching and consistency measurement are established concepts. An agent-specific label would not supply the missing contribution.

Before further runtime work, a proposal would have to establish all of the following:

1. A substantive distinction from existing API consistency tests, observer-effect testing and benchmark-oracle audits, supported by methods rather than keyword absence.
2. A causal comparison that varies only the observer's pre-read, retains a write-bound independent state reference, and records timing, identity and cache evidence. A repaired test that merely passes is not such a comparison.
3. An independently selected evaluation population, with qualification separated from evaluation and all eligibility losses retained. The exposed GitLab trace could motivate or develop the instrument but cannot be recast as held-out validation.
4. A practical consequence beyond finding stale reads, such as validated verdict disagreement or interface-comparison distortion, plus an information-matched established baseline.
5. A bounded budget and stopping rule fixed before outcomes, including the possibility that no generalizable effect is observed.

These requirements are a go/no-go gate, not a new registered study. Existing evidence does not yet meet them. No repair, replacement or rerun of the closed README schedule is proposed here.
