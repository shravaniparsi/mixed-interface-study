# Memos source inventory before ordinary qualification

Pinned release 26.11.0, commit `b40d8a7b573774c52b022c8d6537d6baf2129dc0`. Deployment reachability is already established; no ordinary workflow or boundary collection has run. Source inspection is prior exposure, not a held-out evaluation.

Source root: https://github.com/usememos/memos/tree/b40d8a7b573774c52b022c8d6537d6baf2129dc0

## Prospective resource priorities

Keep the protocol's memos and editable user preferences. The GENERAL preference resource is one workflow; locale/theme/visibility variants do not become independent workflows. The preferences UI saves individual changes immediately, so qualification must observe the actual native mutation and fresh readback, not invent a form-wide Save action.

- `proto/api/auth_service.proto`: POST `/api/auth/signin` accepts password credentials; the response contains an ephemeral access token and the refresh token is an HttpOnly cookie. Keep all authentication material out of traces and screenshots.
- `proto/api/user_service.proto`: POST `/api/users` creates the first administrator; subsequent ordinary users can be created by that administrator. Test with a separate USER actor, not the bootstrap administrator. User-setting reads and changes are owner-only. GENERAL supports locale, memo visibility, theme and save-media-metadata with explicit update masks. Creation of a memo view exists too, but no additional workflow has been selected based on outcomes.
- `server/api/user_service_settings.go`: GENERAL updates merge masked fields into the existing/default setting. Memo visibility is explicitly restricted to PRIVATE/PROTECTED/PUBLIC. Theme and locale are assigned in this handler without an enumerated-value check. This is a source hypothesis; conversion and frontend fallback behavior still need inspection and observation.
- `web/src/components/Settings/PreferencesSection.tsx`: theme, locale and visibility changes each issue a corresponding one-field update mask; the save-media-metadata switch independently persists a boolean. Proposed unrelated continuation: toggle this switch and preserve the three preference strings. Device-local link-preview/double-click preferences must not be mistaken for server resources.
- `ThemeSelect.tsx` and `LocaleSelect.tsx`: theme uses explicit options and an empty-value `system` fallback; locale delegates to LocalePicker and global locale loading. Unknown options or fallback display are not automatically corruption. Establish a display policy before interpreting differences. Underlying values and persisted strings remain separate observations.
- `proto/api/memo_service.proto`: POST `/api/memos`, GET/PATCH `/api/memos/{uid}`; update masks select writable fields. Default audience PRIVATE. Attachment and relation mutations have separate semantics; no upload or external resource is required for the first ordinary memo control.
- `web/src/components/MemoEditor/edit/services/validationService.ts`: saving requires trimmed content, an attachment or a local file; loading/upload/transcription/recording also gate saving. Invalid managed-attachment references have a client check explicitly described as anticipating server rejection. No network-dependent attachment case should be added implicitly.
- `web/src/components/MemoEditor/edit/services/memoService.ts`: native updates include only changed fields in the mask, with timestamps updated for content/attachments/relations/location changes. Proposed unrelated memo continuation: change audience while preserving content. A full declared-field API baseline must be distinguished from native masked writes and output-only fields.
- `AudienceMenu.tsx`: available audience options depend on space placement; use an ordinary personal memo with no space, then qualify actual menu labels and selection. Do not synthesize unsupported UI choices.
- `server/api/memo_service.go`: creation delegates to `prepareMemoCreate`; update requires a mask and owner/admin authorization. The content condition cannot be inferred from this entry-point alone; inspect the helper before freezing candidates.
- `web/src/router/index.tsx`: native memo detail `/memos/:uid`, authentication routes under AUTH, preferences behind authenticated/full-initialization guards. Exact route constants and initial setup requirements remain to be checked.

## Qualification still required

Inspect pinned creation/update helpers, preference defaults/fallbacks, route constants, actual transport (native RPC versus REST), instance version endpoint, actor bootstrap and UI editor bindings. Register two independently reset ordinary pairs per eligible workflow with reversed order. Record raw responses and native values before assertions. No Memos boundary inputs or normalization policy are frozen by this note, and no API/UI difference is an experimental finding yet.

## Additional transport and setup inspection

`web/src/connect.ts` configures Connect RPC with `useBinaryFormat: true`, at the application origin. Native saves therefore cannot be observed by assuming a REST PATCH with JSON. Preserve the actual request bytes, decode against pinned protobuf field definitions, and qualify that decoding against both ordinary payloads and persisted readback. Do not switch the application's transport to simplify measurement.

`proto/api/instance_service.proto` exposes `/api/instance/profile` with version, build commit, demo flag and needs_setup. `web/src/router/routes.ts` resolves auth to `/auth` and settings to `/setting`; `pages/Setting.tsx` selects its section from the hash. `PasswordSignInForm.tsx` and `CredentialFields.tsx` identify `#signin-username`, `#signin-password` and the form submit button. All authentication RPCs must remain outside retained request traces.

`server/api/memo_create_helpers.go` validates audience and placement, checks content quota, rebuilds the memo payload, and resolves attachments and relations before mutation. It does not itself establish the complete content-validity contract; quota and payload helper behavior remain dependencies to inspect. In particular, the UI's trimmed-content rule must not be labeled API-absent merely because it is not visible in this helper.


## Preference display policy and actor bootstrap

Further pinned-source inspection establishes `/setting#preference` as a basic-user section (`settingSections.ts`). `PreferencesSection.tsx` exposes the server-backed media-metadata switch with a translated aria-label, disables it while updating, and sends only the save_media_metadata mask. The API comparator should separately exercise the complete four-field GENERAL update and check preservation of locale, theme and memo_visibility.

`utils/theme.ts` declares system/default/default-dark/paper. Invalid theme resolution deliberately falls back to default; user-preference selection falls through valid localStorage and then system. `utils/i18n.ts` similarly falls through valid localStorage and browser-language matching; loadLocale validates and normalizes for local display. These helpers modify device storage/display, not by themselves the server preference. Fresh browser contexts, fixed browser locale and color scheme are required for paired observations. Record persisted strings, selector state and resolved display separately; an intended display fallback alone is not an unrequested persisted edit or a confirmed defect.

`server/api/user_service.go::CreateUser` validates username/password/email, assigns the first account ADMIN, and lets an authenticated ADMIN create a separately specified USER. Test accounts must be bootstrapped privately, then ordinary resource operations authenticated as that USER. `proto/api/common.proto` declares NORMAL and ARCHIVED lifecycle states. `user_service_converters.go` copies stored GENERAL strings and boolean directly when the setting exists, falling back to getDefaultUserGeneralSetting only when absent. The default helper's definition still needs inspection before registration.

No boundary candidates or results are added by this source inspection. Native binary payload decoding remains unqualified.


## Memo editor binding inspection

Pinned MemoActionMenu.tsx exposes the More button and Edit menu item. MemoView.tsx identifies the editable node as `.memo-editor-root[contenteditable="true"]`. MemoEditor/edit/Toolbar/EditorToolbar.tsx calls the existing-memo commit button Update, not Save. AudienceMenu.tsx labels its trigger with the current audience; a personal memo can select Protected (Anyone signed in). Capture loaded content, current audience, commit-button validity and fresh final readback. Use a uniquely scoped memo card/editor; ambiguous page-level More buttons must fail qualification.

The native memo service includes name and content in its patch even when only visibility changes, but adds only visibility to the mask in that case. It adds update_time only for content/attachment/relation/location edits or explicit timestamp changes. Thus the prospective unrelated audience edit should preserve content and timestamps, subject to source/server qualification. This is source reasoning, not an observed control result. Memo binary request schema and ordinary paired execution remain to be implemented.
