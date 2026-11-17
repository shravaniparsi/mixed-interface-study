# Evidence policy for intended API obligations

This policy is fixed before reserved implementation or correctness outcomes are read. It defines evidence requirements; it supplies no labels and does not register an executable evaluation. A later study must freeze its annotation schedule, selected operations, bounded source access, cases, method versions, adjudication process and analysis before outcomes.

## Distinct questions

Keep three measurements separate: frontend behavior under a particular state, conformance to an API specification, and intended task/workflow correctness. Native validator replay can reference the first. A pinned specification can reference the second, including when generated from backend annotations. Neither alone establishes the third. Report the reference type for every case; do not pool implementation agreement with independently justified defects.

## Label record

Every proposed intended-obligation label records the project/revision, operation, actor, lifecycle stage, request or resulting state, field path, predicate, applicability and cited evidence location/hash. Record when and how the source was obtained, its authorship/provenance where established, and whether it derives from frontend or backend implementation. Unknown provenance remains unknown. Record contradictions and legitimate interface-specific differences, including API defaults, partial updates, generated values, confirmation fields, disabled fields and asynchronous decisions.

A resolved satisfied/violated label requires an explicit pre-existing requirement or behavioral acceptance assertion whose scope covers that exact API operation or required subsequent workflow. It must be separate from the frontend validator being evaluated, from the candidate's output and from its replay comparator. Tests are evidence only after checking what behavior their assertions specify, whether they simply duplicate implementation rules, and whether setup and actor/lifecycle match. An API specification explicitly governing the case supports specification-conformance labeling; calling it independently intended task correctness requires additional provenance/support. Generic prose, UI error text, field names, successful HTTP status, a constraint on another operation, or schema omission cannot supply an intended-obligation label.

Do not read issue fixes or post-defect patches to construct evaluation predicates. No new human-authored expectations based on observed method outputs may be treated as pre-existing ground truth. Synthetic boundary cases can test behavior once an obligation is independently supported, but do not create independent natural defects or projects. Missing or contradictory evidence yields unresolved labels retained in the frame. Labeling uncertainty is not a method success or failure.

## Separation from acquisition

Freeze and store each method's rules/predictions before releasing additional correctness-only evidence. If a requirement is provided to every method as an input, disclose that shared information and measure any frontend contribution beyond it. Do not allow C privileged access to correctness labels while denying the API-only or replay baseline the same acquisition inputs. Access logs must distinguish acquisition documents from reference-only evidence. Since assistant execution is not a blinded human annotation study, do not claim independent human agreement or measured labor savings without actually collecting them.

No adjudicator may repair or selectively exclude a method result after seeing its correctness label. Predeclared unsupported syntax, installation failure, unresolved labels and missing specifications remain separate outcomes with full-frame denominators. Count project/family clusters conservatively; multiple payloads, fields or methods do not increase the independent application count. Before scientific execution, define a minimum informative sample/effect target and a stopping rule. If reference coverage is inadequate, report the study as infeasible or exploratory rather than converting implementation disagreements into confirmed defects.
