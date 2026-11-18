# Continuation-method claim/source check

Applied claim-source-verification with a separate fresh-context skeptic. Four
claim/source pairings were checked: three narrow claims confirmed and one
unsupported generalization rejected. This is a bounded check, not a systematic
review or proof of an unoccupied research area. No manuscript claim was added.

| Claim | Verdict | Primary source and short support |
| --- | --- | --- |
| Current OWASP guidance covers downstream checks after modifying frontend-constrained parameters. | Confirmed | [WSTG-BUSL-01](https://wstg.owasp.org/latest/4-Web_Application_Security_Testing/10-Business_Logic/01-Business_Logic_Data_Validation/): “compare the response, the stored data, and any later behavior”. |
| UI activity can be used to generate API tests and specifications in existing research. | Confirmed | [Carving UI Tests to Generate API Tests and API Specification](https://arxiv.org/abs/2305.14692), 2023: “automatically generates an API-level test suite, along with an OpenAPI specification”. |
| ARMeta uses LLM agents for REST metamorphic testing; it is a 2026 work. | Confirmed | [ARMeta primary record](https://arxiv.org/abs/2605.28321): “uses an LLM-based multi-agent workflow to support metamorphic testing of REST APIs documented with OpenAPI”. |
| These sources prove that no novel contribution on API-created states blocking later UI editing is possible. | Rejected: does_not_support_claim | Neither adjacent techniques nor testing guidance prove impossibility or exhaustive coverage. |

OWASP latest is mutable guidance, not an empirical evaluation or evidence of
historical priority. ApiCarv's tested contribution concerns API carving and
specification inference; it does not by itself establish the proposed later-UI
editability oracle. ARMeta's record reports COMPSAC 2026 acceptance; independent
proceedings metadata was not verified. Do not conflate ARMeta with the distinct
ICST 2020 metamorphic security-testing paper. A search of current notes/protocols/
manifests found no matching ARMeta/2020 conflation to edit in those files.

Decision: do not claim novelty merely from frontend-validation bypass, later
effect checks, UI-derived API tests or agent-based metamorphic generation. A
potential contribution still needs a precise method and empirical result.
Transport normalization alone does not establish that contribution. No new
application cohort, outcome inputs or runtime attempts are authorized here.
