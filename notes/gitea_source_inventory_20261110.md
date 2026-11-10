# Gitea source inventory before ordinary qualification

Pinned release28.3.0, source4f5a3e13e5f3aca85d830e3a9024c893b0bbf1e1, image and HTTP qualification from the first production-extension-screen run42874085809. Fixed workflow priority remains issues, milestones, labels. No ordinary or boundary resource run has been executed.

Source root: https://github.com/go-gitea/gitea/tree/4f5a3e13e5f3aca85d830e3a9024c893b0bbf1e1

## Milestones

modules/structs/issue_milestone.go create fields are title, description, due_on and state. The title field has no Required binding tag here, unlike issue/label create titles. Edit title uses a value string, description/state pointers, and an optional due_on supporting explicit null or empty removal. routers/api/v1/repo/milestone.go only replaces title when nonempty. Do not confuse a no-op update with preservation success without checking the intended edit.

Native milestone_new.tmpl is shared by create/edit. Title input is required with maxlength50; date input is type=date; description uses the shared Markdown editor. services/forms/repo_form.go enforces Required/MaxSize50 on native title. Proposed unrelated continuation changes description while preserving title and due date; actual editor implementation still needs qualification. API full update must supply all four writable fields, retaining null deadline semantics.

Native milestone.go parses a date into end-of-day timestamp, while API create consumes an RFC3339 timestamp. This is exposed source behavior, not an unseen discovery. Ordinary date controls should use the same day-end representation before any time-of-day exploration, and any intended date-only policy must be distinguished from unexpected loss of stored information.

## Labels

issue_label.go API create requires name and color, with description/exclusive/is_archived. API update uses pointers for all five fields. The handler normalizes color and sets archived using a pointer-presence/value expression; a competent full-body baseline must supply is_archived to avoid an omission artifact.

The native label edit modal binds title required/max50, description max200, and color required/max7 with a three-or-six-hex-digit pattern and optional leading hash. Save is an approve button outside the form, so browser attributes alone do not prove submission blocking. Native code also edits exclusive_order, which the API struct does not expose; retain it as readback/preservation metadata if returned, rather than pretending it is an API-writable field. Modal JS submission and color normalization still need inspection.

## Issues

CreateIssueOption requires title and includes body, ref, assignees, due_date, milestone, labels, projects and closed. EditIssueOption includes title/body/ref/assignees/milestone/projects/state/due_date/unset_due_date/content_version, but labels use a separate endpoint. Full continuation must respect this split. Native issue title form uses TrimSpace/Required/MaxSize255; identify the actual edit view before transferring create constraints to continuation. Content version is an explicit concurrency precondition and must be recorded, not stripped indiscriminately.

## Next qualification requirements

Inspect native issue/label edit JS and Markdown editor, ordinary nonadmin actor/repository bootstrap, API response shapes, source-bound DOM fields, and preservation/readback inventories. Qualify reversed-order ordinary pairs and deliberate measurement probes before registering a finite boundary inventory. All descriptions above are source exposure, not application findings or novelty claims.

LabelEdit.ts confirms the approve handler explicitly checks and reports form validity before submitFormFetchAction, despite the outside-form Save button. It also turns exclusive off when a label name lacks a slash-delimited scope and toggles the exclusive-order editor. This is a source-declared cross-field rule to credit to both consistency baselines, not a native-only discovery. Ordinary controls should use a scoped label name when exercising exclusive state.

The shared Markdown editor defaults to a real textarea.markdown-text-editor; the optional legacy EasyMDE switch is a user preference. Isolated contexts should start with the default editor. Native milestone date clearing writes an empty date input. Gitea deployment already passed on the first screen; do not confuse it with second-attempt Vikunja setup. The CLI user-create command supports nonadmin accounts with --must-change-password=false; any generated credentials/tokens must remain private bootstrap material.

## Ordinary milestone/label registration

The pinned image resolves to sha256:361e24f5ef63c7ff4af6a571371511bbc677d8b291dd597c12f338e36ae48b77. docker/root/usr/local/bin/gitea wraps /app/gitea/gitea with /data/gitea paths; CLI bootstrap runs as git with explicit /data/gitea/conf/app.ini. Passwords enter via stdin and CLI output is private. Separate bootstrap admin and study-actor accounts ensure the tested actor is not the initial administrator. The actor's PAT is scoped to write:repository, write:issue and read:user; authenticated GET /user must confirm nonadmin identity.

Four ordinary pairs cover milestone/label in reversed branch order. Repository is empty and synthetic to avoid unrelated Git commit timestamp variation. Milestone uses a UTC day-end due_on matching native date-only semantics; label uses area/ordinary with exclusive=true. Both continuations edit description and preserve all remaining returned target fields, excluding only updated_at. API bodies include all four/five writable fields respectively.

routers/web/web.go confirms milestone POST /milestones/{id}/edit and label POST /labels/edit. Native milestone form is URL-encoded; LabelEdit.ts uses fetch-action.ts, whose prepareFormFetchActionOpts builds FormData. The observer handles both actual content types, preserves duplicate fields, excludes file uploads, and redacts CSRF values including encoded forms. A local parser test covers URL-encoded duplicates and multipart fields. This does not replace runtime qualification. Issue workflow still requires its own ordinary source binding and controls.

## Ordinary attempt1: repository-create scope correction

Run42908370077 at sourcef659611 retains all4attempted pairs,0qualified. Both branches authenticate as nonadmin actor2, but POST /api/v1/user/repos returns403 with required=[write:user]; the initial token carried write:issue,write:repository,read:user. No target milestone or label is created. This is bootstrap qualification failure, not a domain finding.

Controls-v2 replaces read:user with write:user, retaining write:repository and write:issue. Actor role, resource payloads, native observer and preservation rules are unchanged. The original raw403s, command traces and qualification result remain archived. The broader self-user token scope does not make the actor an instance administrator.

Independent control verifier v2 tightens the paired-state flag: missing prefix/final records can no longer compare equal merely because both are absent. Version1's failed bootstrap proof already qualified0pairs; its raw records and proof remain unchanged. The correction changes bookkeeping for incomplete attempts, not application outcomes or the ordinary qualification gate.

## Ordinary attempt2: native response capture correction

Run42909016411 at source9e58ce1 retains4pairs,0qualified. All4API branches pass. Milestone native writes return303 with Location=/study-actor/study-repo/milestones; attempting to read redirect bodies throws and caused an unhandled capture promise. Label native writes return200, but delayed body reads fail after the application's own navigation. Neither attempt reaches mandatory fresh-final DOM verification; successful HTTP alone does not qualify these pairs.

Controls-v3 explicitly marks302/303body as not applicable and retains status/location. Nonredirect body reads begin immediately in the response callback, before file saves or form parsing. Capture errors are retained as ancillary response-body unavailability, while actual native request payload, three DOM views and complete stored preservation remain mandatory. Promise rejection is handled immediately and still propagated through awaited capture work. No target payload, actor, scope, or success/preservation criterion changes.


## Ordinary attempt3 and issue qualification registration

Run42909599730 at source574c5fd qualifies all4milestone/label pairs, independently reconstructed from raw requests, three native views and complete target preservation. No boundary writes have yet executed.

Issue view_content.tmpl scopes the original body to .issue-content-comment; its context-menu edit opens an inline Markdown textarea. Native POST /issues/{number}/content submits content, context and exact content_version. It does not resubmit title. view_title.tmpl contains a separate title editor with maxlength255 and no required attribute; create-form Required must not be assigned to the body continuation. repo-issue-edit.ts forwards the version from the DOM and updates it after success. API EditIssue returns201, not200, and supports optimistic locking with the same version precondition.

Two ordinary issue pairs use reversed branch order and full nondeprecated ten-field API PATCH. Empty attachment/label/assignee/project collections, null milestone/deadline, empty ref and open state are explicit fixture checks, not assumptions. Body is the sole business edit; content_version must increase by one. Within-branch full returned state excludes only updated_at; cross-reset additionally excludes root created_at and embedded user created/last_login timestamps. A native login may change last_login; if so, capture and correct the timing design rather than silently excluding that mutation within a branch. No boundary inputs authorized by this registration.


## Issue ordinary attempt1

Run42910547845 at source0506c9e qualifies0of2pairs. Both full API branches pass; both native writes submit the correct edited body and final API readback confirms it. The fresh editor read occurs before asynchronous Markdown initialization copies raw content into the textarea, producing an empty early observation. The adapter must wait for textarea value to equal independently loaded raw-content, without assuming the desired outcome. Login also changes embedded actor language and last_login, so version2 performs identical native authentication setup in both branches before producer creation, retains the exact within-branch user object, and records authentication setup time separately. No stored-body-loss claim follows from this measurement failure.

## Qualified probes and finite execution

Run42910776570 at source20a64a3 qualifies both milestone/label probe pairs. Actual title inputs reject empty values and accept50characters; attempting51characters via normal browser input yields50. Label color accepts#336699 and rejects invalid; changing name to unscoped clears exclusive. Fields are restored and the complete persisted target is unchanged before the ordinary edit. These are measurement controls, not application boundary results.

Issue run42910920390 at source548a0cd qualifies both reversed-order pairs. Awaiting source-bound raw-content/editor agreement resolves the early empty observation. Both branches authenticate before producer creation, and embedded actor data is preserved exactly during the edit.

Finite inventory is frozen before boundary writes:24generated,19selected,5unselected,12ordinary controls across3workflows. Milestone has7title boundaries; label has12selected name/color boundaries, including source-declared name/exclusive dependence. Issue-body editor is field-local with no required/max-length constraint and no title resubmission; its four controls remain in coverage, with zero generated boundary inputs. Do not transfer the separate title-editor constraint into this workflow.

Nine bounded batches run at most3jobs concurrently. Each milestone/label batch begins with its linked valid pair and skips its boundaries if that gate fails. Register19initial boundary pairs and12valid pairs; repeat every differential, preservation discrepancy, uncertainty or shared-consistency signal twice with its original valid control. Retain the generated/unselected inventory and all failed attempts. No paid calls. Independent reconstruction passes8retained valid branches; adversarial tests reject missing API fields, mismatched native payloads, and an extra preserved-field change. Issue auth setup is shared initialization, not API continuation cost. No inference about native-only benefit follows from these controls.
