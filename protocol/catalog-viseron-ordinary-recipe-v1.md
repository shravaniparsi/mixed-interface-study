# Viseron ordinary user continuation recipe v1

Status: source-derived and pending runtime qualification. This recipe and the input schedule do not authorize scientific dispatch. Use the existing fixed-cohort limits and the pinned Viseron revision 3d77e324d8316033f30acb83058736aa7e468d81. Runtime deployment, complete phase orchestration and evidence verification remain to be registered before an application job starts.

## Selection and values

The selected candidate is the admin AddUserDialog → UserDialog workflow at /#/settings/users. manifests/catalog-viseron-workflow-selection-v1.json preserves six earlier tree-identified dialog paths as unresolved. Do not call this the exhaustively first eligible workflow. It is the first completely source-mapped candidate chosen under the explicit unresolved-prefix provision; runtime eligibility remains unproved. Retain the whole fixed-cohort denominator and do not substitute another Viseron workflow after failure.

Use the synthetic actor and target values in manifests/catalog-viseron-input-schedule-v1.json. The actor is the locally onboarded admin; the target is a separate read-role user. Passwords in that manifest are public test fixtures for the isolated disposable application, not credentials for any real account. The ordinary continuation changes name to Study Edited. For name omission/null cases the unrelated edit is username to studyedited; for username omission/null cases it is name to Study Edited. These choices are frozen before runtime or schema outcomes. The five scheduled inputs are correlated cases in one workflow, not five independent defects.

Password is not a supported mutation target because it is changed in a separate dialog/endpoint, outside the selected editor. Role is a categorical choice rather than an independently editable text control. Do not add these or other classes after observing outcomes. Confirmation password is native form state and is absent from the producer JSON.

## Original native contract

The producer body has exactly name, username, password and role, sent as JSON to POST /api/v1/auth/create. Original create trims name and trims/casefolds username. Ordinary values deliberately contain neither edge whitespace nor uppercase username characters; any later normalization must be reported as normalization, not a defect. Success must include both an original successful response and persisted list/ID readback. A successful create response does not contain the new ID: resolve the single matching username from /auth/users, then read /auth/user/{id}. Assert uniqueness and stable ID rather than using a list position.

The editor initializes from persisted name, username, role and assigned_cameras. Its hook emits exactly name, username, role and assigned_cameras to PUT /api/v1/auth/user/{id}; empty camera selection is serialized as null. Preferences, enabled and ID are not JSON body fields. materialize_viseron_user_update_v1.mjs implements that source mapping, including representation guards. It is not certified for malformed persisted representations outside those guards. Preserve such observations and mark a counterfactual API comparison unavailable rather than filling missing values by guesswork.

viseron_native_controls_v1.mjs uses normal navigation, visible controls, fill and click. It checks the original read-role default, exact create payload, exact materialized update payload, successful response and UI closure. Returned request envelopes contain authentication headers and must remain private; publish only a deliberately redacted evidence report in the future orchestrator. The module does not launch a browser, bootstrap an actor or execute scientific cases. Its readback verifiers require all seven original user fields and preservation of every unedited property. Selector matching, default values and these strict ordinary checks remain runtime hypotheses.

## Authentication and comparisons

Onboard through the original UI, then preserve its cookies and localStorage. The same actor and token type must serve both branches. The frontend uses its header/payload token with the signature cookie, XSRF cookie/header, X-Requested-With and client UTC offset. Capture original requests before implementing the API branch; do not substitute a personal token or omit relevant authentication/transport context. Verify token expiry and detect refresh requests; do not ignore refresh-induced state changes.

Native and API ordinary producers may generate different IDs and salted password hashes in separately initialized fixtures. Record these expected creation differences explicitly and compare complete intended fields without claiming byte-identical independent creations. Matched continuation branches must instead restore the same seed, target ID, actor, browser state and full relevant persistence state. The API branch must use the complete native-matched materialized update, not the producer body or a reduced patch.

Preschedule the warm ordinary continuation before stopping its application instance. It must demonstrate original editor actionability, complete emitted update agreement and the intended persisted change. Separately qualify the restored native/API pair from one captured seed. Compare warm target semantics, actor and payload against the restored controls while retaining differences in full-state history; do not claim full fresh/warm state equivalence from a semantic check. Any state-history discrepancy that could explain the scientific comparison must be resolved before admitting evidence.

## Original schema and restoration

The S baseline is the original executable Voluptuous create schema (0.16.0), selected from the original route object by evaluate_viseron_original_schema_v1.py. It is not a translated JSON Schema, and schema acceptance alone is not evidence of successful creation. Require successful pinned-package inspection and ordinary agreement with actual request handling before its use. Missing or incompatible execution remains unavailable.

Use catalog-viseron-checkpoint-design-v1.md for database and configuration-volume helpers. Actual restart/restoration, camera-free setup, local-only service networking, compiled frontend provenance and complete browser/API phase orchestration must pass runtime qualification. Unit tests do not satisfy these gates. No Viseron application job or altered producer input has run at this freeze.
