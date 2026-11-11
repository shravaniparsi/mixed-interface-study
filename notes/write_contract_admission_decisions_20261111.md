# Historical corpus admission decisions

## Superset: ambiguous contract, not dispatched

Lead 3 is retained as an ambiguous pre-repair contract and excluded from this bounded runtime expansion. This applies the previously registered instruction to retain ambiguous contracts rather than assign violation labels. It does not assert that the maintainers' fix was unnecessary or incorrect.

At 05c6a590e39698f5612fd548efd31f06736a2fd5, UpdateChartRequest.validate_column_patch in superset/mcp_service/chart/schemas.py explicitly describes config as a full visualization replacement. The repair changes no schema file. Issue 44176 itself acknowledges the full-config documentation and asks that omitted-preserve versus omitted-reset behavior be decided. Merged PR 44188 defines a bounded preservation choice for color_scheme and row_limit, including explicit-null/default overrides. That supplies a useful repair contract but does not resolve the original full-replacement wording into an unambiguous general preservation obligation.

Sources: [issue 44176](https://github.com/apache/superset/issues/44176), [PR 44188](https://github.com/apache/superset/pull/44188), [pinned schema](https://github.com/apache/superset/blob/05c6a590e39698f5612fd548efd31f06736a2fd5/superset/mcp_service/chart/schemas.py). The PR description also says the work was AI-assisted and claims no independent human review; merge status is not independent experimental verification.

No Superset application runs or paid calls occurred. Existing source inspection remains preserved. No replacement lead was added.

## Vikunja: admitted for registered execution

Lead 4 has an explicit historical field-mask preservation obligation in pkg/models/bulk_task.go, exposed through the bulk route and MCP action. Issue 4109 and PR 4166 describe its violation and repair. The protocol and observer are frozen separately before dispatch.

The later PR base is divergent from its head, so the selected historical revision is bbe3dbe0f7cf97e646f3001c380f59ef5c1cda0a, immediately preceding the first repair. The final repair head is ad018d4e16e8c82ed254376f49d097559524e649. Both have identical dependency manifest/checksum blobs. This avoids silently introducing unrelated base-branch changes.

Source admission does not mean successful reproduction. Runtime qualification and artifact reconstruction remain required. Existing app exposure and issue-driven selection prohibit unseen efficacy or prevalence claims.
