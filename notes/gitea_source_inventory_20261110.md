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
