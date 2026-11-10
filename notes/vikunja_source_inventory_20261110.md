# Vikunja source inventory before ordinary qualification

Pinned release v2.8.0, source 6e788bf87cebe50e2b8d034b213fcf94ae5449ee. Image digest and writable deployment configuration remain those recorded in production-extension-screen-v2.json. HTTP reachability passed; no ordinary resource control or scientific boundary has run.

Source root: https://github.com/go-vikunja/vikunja/tree/6e788bf87cebe50e2b8d034b213fcf94ae5449ee

## Workflow priorities and transport

Retain protocol candidates projects, tasks and labels, subject to source and native qualification. Do not replace a resource because it lacks findings. pkg/models/api_routes.go explicitly distinguishes API versions: v1 uses PUT create/POST update, v2 uses POST create/PUT update, with PATCH for partial updates. Frontend client/generated/sdk.gen.ts and client/queries modules use generated endpoint functions. Confirm the frontend base URL/version before selecting API paths; old model swagger comments alone are insufficient authority.

frontend/src/stores/auth.ts implements registration then login using generated auth operations. Login.vue binds username through #username in #loginform and delegates password to Password.vue. Ordinary actor setup, exact response statuses, token handling, API info/version, route constants and private bootstrap still need qualification. Do not assume a generic admin or use authentication anomalies as domain findings.

## Projects

ProjectSettingsEdit.vue edits title, parent, rich-text description, identifier and color. Identifier FormField has maxlength=10. The title field does not declare required or maxlength in this view. Save is a CreateEdit primary action and is gated on loading state, not necessarily native form validity. FormField forwards attributes to its input; actual DOM attributes must be recorded. The proposed unrelated edit is a title rename, preserving identifier/parent/color/description and other writable state. Do not choose a title boundary when title is the continuation edit.

pkg/models/project.go declares title required with rune length1..250, identifier rune length0..10 and hex_color validation. parent_project_id is a pointer with documented write semantics: omission leaves parent unchanged; explicit0 detaches and requires project-admin permission. API response normalizes a top-level parent to0. This is documented intentional behavior, not corruption. A normal owner may have project-admin rights without being a system administrator; record both identities/permissions precisely. Returned views, subscription, permission and background metadata are not ordinary writable fields. Read full records before freezing the exact preserved/writable inventory.

## Labels

ListLabels.vue allows an owner to open a label edit form via the .label-edit-button. Form includes title, rich-text description and ColorPicker. No explicit title required/length attribute is present in this view. Native mutation projects id/title/description/hex_color through client/queries/labels.ts. pkg/models/label.go declares title length1..250 and hexcolor, normalizes hex on create/update, and explicitly updates title/description/hex_color. Generated API/v2 request validation must be inspected before calling those model tags the complete server contract. Proposed unrelated edit is title rename, preserving description/color; title constraints remain server checks, not invented frontend constraints.

## Tasks

components/tasks/partials/Heading.vue uses a contenteditable h1 with title aria-label, blur/Enter save, and a trimmed title display. Its save handler rejects a trimmed-empty edit locally, restores the prior title, and otherwise supplies the task through useUpdateTaskMutation. That rule is on editing title; a meaningful unrelated continuation must use another actual native editor (e.g. description) and preserve title. A trimmed loaded title is not automatically a persisted mutation. Task update field projection, server validation, route binding and all preserved fields remain to inspect.

## Color representation and prior exposure

ColorPicker.vue uses input[type=color], prefixes # for3/6-character values, and represents empty or CSS-variable values as an empty internal color with a checker pattern. It deliberately does not emit changes merely because the parent model changes, with a source comment referring to issue4156. That is disclosed prior source exposure, not an unseen discovery. An empty color input can have a browser default value while the Vue model stays empty; compare native outgoing payload and stored readback before labeling it a mutation. utils.NormalizeHex and v2 validation still need inspection.

## Remaining qualification

Confirm API version/base URL, actor bootstrap, actual request schemas and update semantics, source/DOM constraints, complete records and metadata handling. Qualify two reversed-order ordinary pairs per eligible workflow and deliberately violating adapter controls before finite boundary generation. No candidate inventory or outcomes are frozen by this source note.

## Ordinary qualification v1 preparation

Confirmed helpers/apiUrl.ts uses /api/v2 and client/http.ts adds bearer authentication. The v2 registration wrapper defaults POST to201; auth login explicitly returns200. user-settings GET /user exposes is_admin. Bootstrap registers a separate first account, then study-actor; the latter must report is_admin=false. Neither passwords nor login token responses are archived.

v2/validation.go runs govalidator valid tags in addition to Huma schema validation. Project native query projection supplies eight writable fields; labels supply three. Ordinary qualification uses exactly those full bodies and the same PUT endpoint as the frontend. It renames title while preserving a nonempty description and nondefault color; project identifier is also nondefault. TipTap.vue exposes .tiptap__editor for source-bound description observation. English source strings confirm Login and Save labels. No invalid inputs are included in this run.

The first qualification run covers projects and labels (two reversed-order pairs each). Task inspection remains pending and is not silently excluded. Full records are retained; within-branch preservation excludes only root updated. Cross-reset comparison excludes only named server timestamp locations: root created/updated, owner or created_by created/updated, and direct project-view created/updated. Unknown metadata is not broadly discarded. Ordinary runtime must still establish whether this projection is adequate before scientific registration.

## Task and rich-text source follow-through

client/queries/taskMutations.ts supplies sixteen writable fields, trims supplied title, normalizes hex color, maps empty date strings to API zero dates, then constructs JSON Patch add operations for each present field. Task description saving spreads the loaded task and changes description; thus it can resubmit other writable values. Description.vue has a five-second autosave and explicit Save, so native request capture must start before editing. Task detail route is /tasks/:id; .tiptap__task-description scopes its editor. Task detail expands is_unread and can mark a task read; read markers must not be mistaken for corruption.

pkg/models/tasks.go limits new/changed titles to1000 runes, validates repeat_after within ten years, and declares priority unrestricted. Do not invent priority range violations from a finite UI selector. Percent_done is documented0..1; enforcement must be established separately. Frontend normalization maps missing/null collections to empty arrays and missing scalar values to defaults; qualification must expose which values the actual pinned API returns before comparator rules are fixed.

v2/richtext.go confirms default HTML on both transports. Markdown conversion occurs only on explicit format=markdown or X-Vikunja-Format: markdown. Its documented lossy conversion is not an unseen defect. utils/normalize_hex.go strips a leading hash and truncates to six characters, after the API's schema/model validation. All these source facts precede any Vikunja boundary experiment.
