# Celerio runtime dependency review, 17 November 2026 (Pacific)

Four pinned files were scheduled and published at eabd1ce before retrieval. All four matched the Git blob and SHA256 checks; cumulative analyst dependency budget is 11/24. No runtime or scientific experiment was executed in this review.

The original AuthService sends a form-encoded POST /api/login with j_username, j_password and submit, and checks GET /api/authenticated. The public seed SQL inserts a synthetic admin/admin account and roles; this is fixture source, not a user credential. Whether the backend accepts that fixture has not been exercised.

The original Angular CLI config emits web/dist. The previously read Maven resources refer to src/main/webapp/aot, so serving a compiled UI requires an explicitly frozen packaging arrangement; the locations are not interchangeable by assumption. AppModule imports @angular/material and primeng/primeng; neither package is declared in the previously collected web/package.json. This establishes a source dependency mismatch, not an observed compiler result. Do not add guessed dependency versions or regenerate the app to manufacture a successful control.

The Author detail component uses the same save handler for route /author/new and existing IDs. AuthorService uses PUT /api/authors/ and GET /api/authors/{id}; email, firstName and lastName remain the provisional scalar fields. Build qualification and native/API serialization equivalence remain unresolved. Database constraints inspected in the seed schema are implementation evidence, not automatically a normative user-facing obligation.

Next action: freeze a bounded original-source build qualification before executing it, preserving dependency resolution and compile outcomes. Complete preceding component dispositions before final workflow selection. A failed build must stay in the nine-project sampling denominator; it must not trigger a replacement application selected for likely findings. The independent study still has zero executed scientific variation cases and no demonstrated Q1 contribution.
