# Runtime configuration as an oracle source: bounded prior-art check

Candidate mechanism: retrieve runtime field definitions, bind them to a declared creation-semantics template, and check resulting resource state. The NetBox issue 18669 calibration tests this mechanism on an exposed historical fault. It does not establish automatic discovery, generality, or novelty.

An independent claim-source skeptic checked three primary full texts. Configuration-dependent testing is established, and API retrieval alone is not a defensible claim of a fundamentally new testing principle.

| Source | What it establishes | Limit of this comparison |
| --- | --- | --- |
| Xu and Legunsen, Configuration Testing, 2019, https://arxiv.org/html/1905.12195v2 | Instantiating parameterized tests with actual configured values and checking their dynamic effects. | Does not establish the specific custom-field metadata retrieval and creation-template binding in the examined text. |
| ARMeta, 2026, https://arxiv.org/html/2605.28321v1 | LLM extraction of REST metamorphic relations and executable stateful follow-up checks; execution failures distinguished from relation failures. | Does not establish this particular runtime metadata interpretation mechanism in the examined text. |
| Alonso et al., Test Oracle Generation for REST APIs, DOI 10.1145/3726524, https://idus.us.es/server/api/core/bitstreams/8062d4b0-2153-4d5c-9a0a-5e607d8a6edc/content | Learning likely invariants from OAS and observed request/response data, with developer confirmation and executable assertions. | Learning observed regularities is different from interpreting retrieved metadata under a declared normative template; neither difference alone establishes novelty. |

This is a bounded comparison, not a systematic review or evidence of an empty literature gap. The exact candidate was not established by these three sources. The intended next feasibility decision is whether a reusable metadata binding adds value beyond an equally informed handwritten configuration rule and existing API semantic tools. The handwritten rule is an information-matched reference, not an unfairly weaker baseline. A status-only baseline is diagnostic only and cannot establish state-of-the-art superiority.

For the registered calibration, both text/default metadata and the semantic interpretation are already known to the researcher. Changing defaults checks that expectations follow configuration rather than a hardcoded value. It does not prove that a generator can identify the relevant configuration endpoint or infer default precedence. Those are separate untested problems. Twelve variants of one repaired bug remain one historical fault.

## Normative scope check after registration

Pinned NetBox documentation at `cac41cd093b7fdcf96e9525bd7c01b5dad4aaedb`, `docs/customization/custom-fields.md`, documents optional default values and custom-field REST representation. It does not fully specify every absent-versus-null precedence case in the calibration. Therefore the documentation alone is not complete ground truth: the historical issue and fixing change inform the rule, while the explicit-value cases test its limits. The source copy and hash are retained in results/netbox-defaults-documentation-v1. This retrieval occurred after registration and did not alter the cases.

A title-only screen of the 440 frozen metadata rows found another documented default-related case, Dolibarr 33949. Its guide describes failure to persist an explicitly requested configuration update, which an ordinary requested-write/readback check should already detect. It is not evidence that a configuration-derived creation oracle adds incremental value. This is an exposed lead assessment, not a new executed exclusion cohort or an estimate of prevalence.
