# Source dependency wave 3 and partial workflow mapping

All 56 scheduled source blobs were collected and verified. Cumulative acquisition is 183 source slots and 1,961,054 decoded bytes across the original twelve projects. The two closed scope exclusions were not revisited. Acquisition counts do not mean that every collected line has been reviewed. No application job, altered producer input or scientific comparison ran.

## Mathesar user candidate

Full review of wave3 files51–56 and the user persistence sources (files48 and50) connects the native administrator user route to UserDetailsForm, JSON-RPC method declarations, the shared endpoint /api/rpc/v0/ and original Django persistence helpers. NewUserPage calls users.add; the existing-other-user branch calls users.patch_other with full_name, username, email, display_language, user_id and is_superuser. The current-user branch uses patch_self and has different SSO/language behavior; it must not be substituted into a same-actor comparator for another user.

The original form initializes full_name and email with nullish fallback to empty strings, username with empty-string fallback, display_language with en fallback, and admin status with false fallback. It declares optional full_name/email, email validation, username required/max-length/regex rules and display-language required. The backend creation helper uses explicit defaults for omitted optional properties and passes explicit null through; its update helper writes the supplied values. The model declares nullable full_name but a non-null display_language field, and inherits other fields from Django. Source-level expectations are not empirical acceptance outcomes.

This establishes a plausible source-mapped JSON user candidate, not a completed mapping or admitted scientific workflow. Still unresolved: shared makeForm/field stores and validators, FormSubmit/actionability, input bindings, exact JSON-RPC envelope/request-id generation, RPC decorators/middleware and original schema availability, inherited Django field definitions, bootstrap/authentication configuration, per-user database side effects, source-to-executable provenance, and supported restoration. No producer values or unsupported input classes are frozen yet. The ordinary recipe must follow actual persisted readback and native normalization; converting null to an empty string through original form logic must be reported as normalization, not fabricated native incompatibility or silent target preservation.

The native path review identifies administration/users/new before database-specific create routes, but common modal helpers and route nesting still require a recorded candidate-order justification. Do not relabel this provisional candidate first eligible until that check is complete. No alternative workflow is selected from expected outcomes.

## Other partial review findings

Full review of sE2EEnd SendController and sendApi (wave3 files43 and46) finds metadata creation, read/list/history, deletion and upload/download operations, with no metadata update operation in those two interfaces. Earlier admin settings are mutable existing policy values, not yet a demonstrated create-and-edit record pair. The dashboard/upload components and other configuration/authentication routes remain to be reviewed before any project-level disposition.

Jitsi poll middleware (file20, full file) clears local poll state on conference changes and consumes poll/answer/closed conference events. It does not demonstrate persistent server JSON create/edit/readback. The inspected poll path remains a candidate-level scope mismatch; this does not by itself establish an exhaustive project exclusion or absence of every persistent extension.

Seatsurfing partial source review shows attributes and groups with a single obvious free-text label/name, and bookings assigning subject plus selected user/space and timestamps. Whether two independently editable scalar text properties remain in the same continuation, and whether earlier routes qualify, is unresolved. Do not silently choose a later location/user form based on anticipated validation outcomes.

Nginx Proxy Manager's partially reviewed first AccessList modal serializes filtered nested items and clients as well as root fields. It cannot be replaced by an easier later modal before resolving eligibility, independent-edit semantics and helper/default coverage. CloudBeaver's TeamForm delegates to state.save and part services; that wrapper alone does not establish a complete request. The earlier configuration/profile forms remain unresolved prefixes. OpenELIS's order entry delegates to form-value builders, utilities and backend validation; optional attachment branches are not automatic proof that a no-upload ordinary path is qualified.

Existing and newly encountered implementation comments are source exposure. For example, OpenELIS order-entry code contains a comment about an earlier duplicate-value save failure. It is not a new executed finding and must not determine test selection. No referenced issue, commit, test or fix history was followed.

Next source schedules should resolve necessary original helpers and setup contracts, with a particular opportunity to complete Mathesar's user mapping, while preserving all ten remaining projects' pending status. The fixed cohort still contains zero independent scientific cases.
