# Contract-inference comparison: verified scope

The claim-source-verification skill was applied with a fresh-context skeptic. Three source–claim pairings were checked: two confirmed and one rejected (`does_not_support_claim`). This checks the scope of two papers, not novelty across the literature.

## Confirmed: before/after API contracts already exist

[IcePick/Glacier](https://arxiv.org/html/2604.08633v1), Ana Catarina Ribeiro, Margarida Mamede and Carla Ferreira, arXiv:2604.08633v1, 9 April 2026, §II-B: “The prev operator captures a value before execution, allowing postconditions to refer to the prior state.” Its executable contracts therefore already support referring to earlier observations. Our shared replay representation is not a new principle on that basis.

## Rejected: automatic CRUD inference covers arbitrary preservation and cascades

The same source, §II-B, limits generated contracts to partial CRUD semantics and describes manual service-specific additions. Expressing a property and inferring it automatically are different capabilities. Inserting update calls into generated sequences (§II-D) does not establish arbitrary partial-update preservation inference. Do not repeat the rejected broad claim, or the opposite claim that this work lacks stateful contract checking. This narrows a possible comparison but establishes no new method for our study.

The [artifact landing page](https://zenodo.org/records/20251054) lists a 2.6 GB framework archive. README and artifact-description file retrieval failed through the browsing tool; the package was not downloaded or executed. No implementation-equivalence or runtime-performance comparison is claimed.

## Confirmed: executable dependencies are not complete correctness oracles

[APIPilot](https://arxiv.org/html/2608.17546v1), Tu Nguyen, Thanh Nguyen, Huy Nguyen, Viet Nguyen, Tien N. Nguyen and Vu Nguyen, arXiv:2608.17546v1, 18 August 2026, §II-B: “Its output is treated as refinement guidance, not as an oracle, and is applied only when validated by later execution.” Sections III-A2 and III-B validate producer–consumer mappings through calls. This supports contextual executability, not complete business correctness. The paper tracks resource state and response evidence, so a claim that it does not check state would be too broad. Its replication package was not executed.

## Consequence

The previous contribution assessment remains negative. Adding before/after checks, generated contracts, or executable workflow dependencies does not by itself supply novelty. A proposed reduction in manual work must identify what semantic information is inferred, how correctness is established independently of the implementation under test, and how it compares with competent contract-generation approaches. Comparisons must not deny capabilities these sources explicitly describe.

RESTOR and additional metamorphic-testing sources surfaced during screening but have not undergone this pass's independent claim verification. They remain leads, not support for a manuscript claim. No quantitative result from those sources is imported into this study.
