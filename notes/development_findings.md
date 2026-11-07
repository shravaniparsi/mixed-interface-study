# First informative development results

6 November 2026, America/Los_Angeles. Source-pinned applications were executed locally without application-code modifications.

The expanded pilot supports a concrete reason to test native UI continuations: a state accepted by the API can prevent a later, otherwise ordinary UI edit. It also supplies a counterexample to an overly broad claim: some downstream failures are detected just as well by competent API checks.

## Reproduced findings

| Case | Immediate response | Equivalent custom API continuation | Native UI continuation | Interpretation |
| --- | --- | --- | --- | --- |
| PetClinic owner named `Anne-Marie`, then change address | Creation succeeds, HTTP 201 | Address update succeeds, HTTP 204, correct readback | Fresh form loads the record, but Update Owner is disabled; address remains unchanged | One reproduced **known compatibility issue** |
| RealWorld duplicate-title article, then body-only partial update | Update succeeds, HTTP 200, but returns a different slug | GET of returned slug gives 404 | Native page GET of returned slug also gives 404 | Reproduced returned-identifier defect; **both continuations detect it** |

PetClinic explicitly permits hyphens in its API name contract. Its frontend uses a narrower alphabetic pattern. The name was left unchanged while the experiment attempted to edit the address. The same API and UI branches started from identical initial and post-creation owner graphs; the valid-name control completed both edits. The result reproduced in a second independently reset pair. The unchanged name displayed no validation message, while submission remained disabled. [Detailed evidence and screenshot paths](../manifests/petclinic-hyphenated-name-evidence.json).

This validation mismatch was already reported upstream on 27 October 2026. It is a known issue reproduced in our workflow, not a new bug discovery. The existing reports describe the pattern mismatch; maintainers have not reviewed our particular reproduction. [Issue 233](https://github.com/spring-petclinic/spring-petclinic-angular/issues/233), [issue 241](https://github.com/spring-petclinic/spring-petclinic-angular/issues/241).

For RealWorld, the original slug still retrieves the article with the updated body, while the slug returned by the update does not resolve. The source explains the difference: saving an article regenerates its in-memory slug, but a body-only partial update omits `slug` from the fields written to the database. The response serializes that in-memory object. A collision with an existing title exposes the disagreement. [Save implementation](https://github.com/c4ffein/realworld-django-ninja/blob/87dd078c883a046f5ff20269df2fb004d8b5f83f/apps/articles/models.py#L51), [partial-update implementation](https://github.com/c4ffein/realworld-django-ninja/blob/87dd078c883a046f5ff20269df2fb004d8b5f83f/apps/articles/api.py#L109).

Body-only updates are supported by the local API and its existing tests. Full-field updates on the duplicate article, partial updates on a unique-title article, and actual native UI updates on the duplicate article all supplied resolvable identifiers and allowed the following comment operation. Two diagnostic repetitions per API/UI continuation reproduced the failure; all 12 diagnostic control executions passed. These are repeated observations of one defect, not separate defects. [Diagnostic run](../results/realworld-boundaries-20261107T055116Z/summary.json). Bounded issue searches found no match for `slug` or `partial`; the fault's prior-report status remains unestablished. [Search record](../manifests/prior-issue-screening.json).

The partial API update and native full-field update are different legal payload bundles. This result supports testing supported API variations and consuming returned references; it is not a payload-identical route-only experiment and does not demonstrate a UI advantage.

## Executed corpus and denominators

| Quantity | RealWorld | PetClinic | Total |
| --- | ---: | ---: | ---: |
| Workflow templates | 4 | 3 | 7 |
| Registered case variants, including controls | 26 | 18 | 44 |
| Main independent replay branches | 50 | 36 | 86 |
| Actual API continuations started | 13 | 6 | 19 |
| Actual UI continuations started | 15 | 6 | 21 |
| Additional diagnostic replay branches | 16 | 6 | 22 |

Each main branch independently restores the initial state and replays the prefix. Many invalid inputs stop at the prefix, so 86 branches do not mean 86 downstream continuations. Two RealWorld native producer controls have only a UI continuation. The remaining RealWorld cases and all PetClinic cases are paired API/UI branches. Workflow counts describe templates, not independent statistical replicates.

The templates cover RealWorld article create/edit, comment create/delete, profile update/edit and article update/comment; PetClinic owner address edit, pet rename and visit rescheduling. The cases were selected using source and contract inspection. They are development data, not a representative prevalence sample or held-out effectiveness evaluation.

## Other observations retained separately

- Eighteen case variants reject the prefix with HTTP 400 or 422. Their API and UI branches stop before any downstream continuation.
- Four case variants return HTTP 500 at the prefix: RealWorld article title length 151 and username length 61, and PetClinic telephone lengths 9 and 11. These are server-error observations, not clean client-error validation responses. The two RealWorld cases also return 500 on the recorded follow-up read, causing four failed unchanged-state checks across paired branches. That establishes unreadable follow-up responses; it does not independently establish database corruption. They remain outside the two adjudicated findings above.
- Whitespace-only RealWorld titles return an empty slug. Both branches stop at a common reference preflight, before any native UI continuation. This is retained as an unresolved reference anomaly, not a UI detection.
- Whitespace-only PetClinic city and visit-description values allow the API edit but block the UI edit. The intended domain rule is insufficiently explicit, so these two cases remain policy ambiguities and are excluded from confirmed compatibility-defect counts.

## Execution corrections and scope

The first RealWorld boundary run completed 50 branches with narrower assertions. An independent code review identified missing unchanged-field and parent checks. Revision 2 reran the unchanged pool with input-to-output field checks, parent-article readback and profile-field preservation. The earlier traces remain under `realworld-boundaries-20261107T054339Z`; the analyzed main run is `realworld-boundaries-20261107T054749Z`. The runner explicitly records whether a continuation actually started.

PetClinic's initial six-branch setup attempt exposed an incorrect date representation in the runner. The runner was corrected to use the native date format, and all three positive controls and the full registered pool were executed again. The failed attempt remains separate. No application behavior was patched.

The comparison is against a custom API-semantic continuation performing the corresponding action and readback. RESTler, EvoMaster and other off-the-shelf tools have not been run. No selector superiority, speed advantage, population effect or agent behavior is established. Independent checks in this session were performed by AI agents; independent human adjudication has not occurred.

## What this changes for the paper

We now have a reproduced example where a native UI continuation supplies information absent from an equivalent successful API continuation. That supports the research question. A single known defect across two sample applications is not sufficient evidence for a Q1 method paper.

The next priority is to test transfer on an eligible application excluded from development, expand the compatibility corpus, and integrate generated candidates with the actual execution/budget controller. Only then should route-aware selection be compared with generic dependency selection under the same candidate pool and oracle. The proposed selector's value remains unmeasured.

The generator now produces an immutable, provenance-bearing 18-case RealWorld pool with explicit unsupported-interface exclusions. This pool matches the registered mutation inputs, but the browser batch still uses its explicit case registry. No automatic discovery of business rules or integration with the runtime budget is claimed. [Generator usage](registry_usage.txt).

Additional paid API/hosting expenditure remains **$0**. Source pins, exact executed runners, initial-state hashes, raw HTTP observations, screenshots and diagnostic runs are retained. The earlier manuscript DOCX remains a prospective draft; this evidence note is the current development result record.

## Recompute and inspect

From the project directory, run `python3 scripts/summarize_development_batch.py`. It checks main-run source/registry hashes and reset evidence, then writes [summary JSON](../results/development-batch-v2/summary.json), [candidate rows](../results/development-batch-v2/candidates.csv) and [branch rows](../results/development-batch-v2/branches.csv). Counts are descriptive; the script performs no significance tests.
