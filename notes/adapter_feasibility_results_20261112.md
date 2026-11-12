# Completed converter feasibility pilot

## Result

Prefect FastMCP 4.1.8 and Punkpeye FastMCP 4.26.2 each preserved the request and resulting database state for all 48 frozen source inputs in both registered repetitions. Across the two qualified subjects there were 192 paired observations: zero advertised-schema-invalid inputs, zero request differences under the declared equivalences, zero persisted-state differences and zero tool-error outcomes. Each completed subject's 576 HTTP events reconstructed consistently with the paired observations and final SQLite file.

These are 48 shared input shapes tested on two converter implementations with two repetitions, not 192 independent workflows, applications or defects. They cover a synthetic five-field source API with two operations. They do not establish ecosystem-wide correctness or the absence of failures on other schemas.

Ivo-Toby mcp-openapi-server 1.18.0 initialized and listed tools but exposed abbreviated names (crt-record and ptch-record) that did not satisfy the frozen operation-name binding rule. It performed no scientific writes. All 48 source cases and 96 planned paired observations remain unexecuted. This is a study binding limitation; it is not evidence that the converter loses input semantics. The rule was not revised after discovery.

## Attempts and cost

Initial run 43163040718 used frozen commit b64f898aae93cc384919da08f5218ee3e86f66b3. Prefect completed, Ivo stopped at binding, and Punkpeye stopped at installation because the lock omitted a required openapi-types peer. One separately registered correction added only openapi-types 12.1.3, preserving every existing dependency version and integrity hash. Corrective run 43163575286 used commit 57d819bf98685e990a2a9c36a5393de776ced626 and completed Punkpeye's fixed schedule.

Four application jobs consumed 133 seconds (2.2167 job minutes), including setup and reference calibration, against the 90-minute ceiling. There were zero paid model calls and no paid infrastructure provisioning. This measures elapsed job time, not verified account charges. Automatic unit-check time is outside this application-job subtotal. Failed attempts are retained.

The preliminary dispatch using a commit SHA was rejected with HTTP 422 and created no job. Dispatch then used main after verifying its head matched the frozen commit. Each actual run's head is retained in the archive and checked in reconstruction.

## Measurement and interpretation

Each route executed against a freshly reset HTTP/SQLite backend. Direct REST qualified for every executed case. The request comparator preserves null/absence, boolean/number distinctions and array ordering while ignoring object-key order and accepting the fixture's two declared PATCH media types. The state check reads the full database, including a sibling record. Captured request semantics and persisted-state results agree here; state checking demonstrated no incremental detection over request comparison.

Before comparison, completed jobs ran the fixed reference-calibration matrix. Its deliberately altered requests are sensitivity controls, not natural converter findings. The offline scorer also reproduced 142 preserved cases, 48 state-difference cases and two request-only differences from those 192 existing control traces. That replay is engineering verification, not a new experiment or additional sample.

## Research decision

Close this cohort. No further repetitions, replacement converter, schema expansion or issue-derived cases are authorized within it. The observed result supports a narrow preservation statement for the two qualified converters on this source fixture. It does not support an assertion that these current converters commonly mishandle omissions, nulls or falsy values.

The broader Q1 goal remains unmet. The prior independent native/API cohort produced no incremental native-only detections; the historical calibration studies are exposed known faults; this new converter pilot is clean and synthetic. Combining these categories cannot create independent natural-defect evidence or a novel method contribution.

Do not move this candidate to a submission-ready empirical defect paper. The next scientific decision must concern a genuinely independent real-workflow sampling frame and a contribution distinguishable from existing differential/state-oracle work. Any future study needs a new prospective protocol and must remain capable of returning a null result. More variants of this fixture are not an adequate next step. The current artifacts can support a transparent feasibility/negative-results report, but Q1 suitability has not been established.
