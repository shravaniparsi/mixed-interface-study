# Historical null-state candidate: source admission review

Protocol frozen and pushed at 9eb0a3f before retrieval. Completed 26 read-only GitHub requests: six initial endpoints, eight endpoints for four directly linked objects (backend issue 23, frontend PR 48, backend PR 43, backend closing commit), and twelve immutable source-file requests. No additional searches, pagination, trees, live previews, installs, application executions, Actions jobs or paid calls. All responses succeeded and their private bytes were hash checked. Public manifest retains endpoint identifiers and hashes; original bodies/profiles remain outside git. Frontend README review covered its first 14,000 characters only; no runtime conclusion depends on its boilerplate. Other eleven source files were read completely.

## What the sources establish

Frontend PR 36 introduced Array.from(camper.setup) in Campers.js. The issue and maintainer comments distinguish empty form values from direct requests containing null. The pinned App.js reads API posts and constructs one Campers component per item. Its native form posts to /api/v1/add, whereas the backend API tests post JSON to /api/v1/posts. These are distinct producer handlers and must not be treated as interchangeable.

Frontend PR 48 replaced the unconditional conversion with an Array.isArray conditional. That source removes the null-sensitive conversion; no React render or browser test was executed. Its stated target was issue 43, and a commenter proposed that it also addressed issue 42. This is independent authored repair evidence, not a verified complete repair of the reported workflow.

Backend issue 23 explicitly links the frontend failure and asks for default values. A comment links PR 43; its merge ea57863bf842c25d0ad1c48420e67a71f6437b78 closes issue 23. The change adds setup default [] in a Mixed schema and a truthiness-guarded typeof check in the JSON producer. Explicit null bypasses that controller check. Whether the historical Mongoose version retains null must be measured before claiming a residual backend failure; the schema default alone is not proof of normalization. The native form producer lacks the added type check. Neither observation is a newly confirmed defect.

The parent backend test already supplies an omitted-setup request with username Gauja and availableTime 1:00, expecting status 201, an empty setup array and persisted state. Thus the project itself supplies an API-level expectation capable of detecting that omission violation. A fair comparator must receive it. Explicit null and property omission remain distinct cases of one reported fault cluster; undefined cannot appear as a JSON value.

## Admission decision

Zero cases admitted. Frontend and backend source revisions and external fix links are recoverable, but exact historically co-deployed revisions, full original request, dependency resolution, isolated runtime, and end-to-end failing/fixed behavior remain unverified. The frontend introducing merge and the later backend fix parent must not be described as a proven historical deployment pair. A new paired runtime would be a reconstructed configuration unless deployment evidence is recovered.

This strengthens provenance for a possible retrospective calibration case. It provides no new-defect discovery, incremental detection advantage, independent multi-project sample, agent improvement or Q1 readiness. The original 50-report frame and fifteen-task frame are unchanged. No second candidate replaces this one after this review.

Next useful work, if undertaken under a new bounded protocol, is a small source-faithful component/schema calibration of null versus omission, with normal-value controls and the existing API predicates. It must be labelled component evidence, not a full application experiment. Full runtime reconstruction should follow only if that calibration leaves a meaningful comparison to test; historical installation success alone does not close the scientific contribution gap.
