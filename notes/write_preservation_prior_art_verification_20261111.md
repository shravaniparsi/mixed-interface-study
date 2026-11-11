# Prior-art verification for the next contribution gate

Fresh-context claim-source verification examined three additional proposed pairings. Two were confirmed after precise narrowing; one remains partial as originally phrased. No complete pairing was rejected. No source establishes that the proposed study is novel.

## Differential Regression Testing for REST APIs

[Primary paper, ISSTA 2020, §§2.3–2.6 and 3.1–3.4](https://patricegodefroid.github.io/public_psfiles/issta2020.pdf).

Supported: cross-version API differential regression testing is established. The method uses generated request sequences and network-log comparison across client/service versions.

Supporting quote: “we compare the behavior of different versions on the same inputs against each other, and find regressions in the observed differences.”

PARTIAL as originally phrased: calling this precisely the same as an unchanged archived reproducer replayed on a known faulty/fixed commit pair overstates the match. Generated concrete names and sequences can differ. The broader antecedent is sufficient to rule out claiming version comparison itself as new. A dedicated replication package was not verified.

## SATORI

[Primary full text, §§III-A–C, Table I, VI](https://arxiv.org/html/2508.16318v2).

CONFIRMED narrow statement: SATORI infers predefined response-field oracles from OpenAPI names, descriptions and examples, then generates executable assertions. Its reported catalog/evaluation is unary: formats, ranges, enumerations, booleans, array sizes and ordering. Multiple-variable oracles are future work.

Supporting excerpts: “We focus on unary oracles to make our evaluation affordable”; “test oracles evaluating a single variable”.

The evaluated catalog does not implement cross-request before/after frame conditions. This is a methods-level boundary, not proof that such conditions are novel elsewhere. The [OKAMI dataset](https://huggingface.co/datasets/javalenzuela/okami-dataset) is accessible. The linked [replication DOI](https://doi.org/10.5281/zenodo.15529767) could not be inspected through the verification tool.

## RESTestBench

[Primary full text, §§3.2–3.4](https://arxiv.org/html/2604.25862v1).

CONFIRMED narrow statement: its benchmark evaluates requirement-to-test translation using verified natural-language requirements and requirement-specific mutants across three REST services. Requirements include multi-step CRUD workflows and cascading state changes; dismissing it as single-response testing would be wrong.

Supporting quote: “Each requirement is formalized as a property, and for each property we define a set of mutations that lead to violations of that property.”

Its requirement–test–mutant unit differs from admission based on an actual reported defect and historical repair evidence, but that distinction alone is not a contribution. The [repository](https://github.com/casablancahotelsoftware/RESTestBench) contains requirements, golden tests, services and results; no code was executed here. Preprint DOI/ISBN placeholders must not become bibliography metadata; use the arXiv record.

## Consequence for this project

The remaining candidate contribution is narrower than semantic API testing: an independently reproducible corpus and evaluation that distinguishes adapter-introduced state loss from shared backend behavior while retaining intended clears and cascades. The twelve-execution Tiller calibration establishes only one backend case and a working observation method. Additional historical cases would establish breadth, not novelty or held-out efficacy. Before expanding execution, compare existing corpora and fix methods, define incremental value and freeze an independent evaluation cohort. Keep the completed negative cohort intact.
