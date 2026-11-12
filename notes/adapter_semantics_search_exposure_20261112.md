# Exploratory adapter-semantics search exposure

After rejecting a novelty claim for the current configuration template, two bounded searches examined MCP omission/null transport and API adapter semantics. No application was run and no implementation or issue report was independently reproduced. These searches establish exposure, not a validated benchmark or a new research gap.

Primary issue pages returned by search (reported behavior, not verified findings):

- https://github.com/pingdotgg/t3code/issues/16809 — reported optional/nullable advertised-schema versus decoder mismatch.
- https://github.com/modelcontextprotocol/kotlin-sdk/issues/581 — reported serialization of absent response members as null.
- https://github.com/zereight/gitlab-mcp/issues/281 — reported insertion of null/default values for omitted arguments.
- https://github.com/modelcontextprotocol/python-sdk/issues/3224 — reported optional output-member null insertion.
- https://github.com/anthropics/claude-code/issues/58794 — reported enum-reference argument serialization issue.

The next researcher must not call these cases unexposed, newly discovered, or randomly sampled. Search snippets alone do not establish root causes, current status, patch effectiveness, or independence between cases. A schema-conformance check may already detect several of them. A proposed adapter-semantic method would need to distinguish ordinary JSON Schema mismatches from schema-valid changes in downstream meaning, then compare against competent schema and serialization checks. Generic omission/null distinction and preservation are not new claims.

No issue-derived replacement is authorized for the closed independent-input cohort. Any future sampling frame must be chosen separately and before observing comparative outcomes. These leads are development/prior-art material only.
