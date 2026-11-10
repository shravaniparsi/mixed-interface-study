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
