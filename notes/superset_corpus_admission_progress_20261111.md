# Superset admission progress

This is source inspection, not an executed experiment or admitted scientific result. Lead 3 in the frozen write-contract expansion protocol.

Repository: apache/superset, PR 44188. The commit chain was checked against GitHub commit metadata:

- Historical base: dd60cc27ff471432f26984b4564e9c6936417365.
- First repair: fd471bbecca7938cd30b50f34f15ff7490c3405c, immediate child of the base; changes shared chart-control merge behavior and its tests.
- Comment clarification: 4925fd6f0682ad48f2b432a90d1fa278610829c6, immediate child of first repair.
- Normalization repair: 05c6a590e39698f5612fd548efd31f06736a2fd5, immediate child of clarification; changes plugin normalization to exclude unset fields.

The first change preserves omitted color_scheme and row_limit during same-visualization merges. The second preserves field presence through normalization. These are stages of one reported repair, not independent defects for each plugin. A staged comparison may be more informative than repeating the final fixed/unfixed pair.

The production entry point is superset/mcp_service/chart/tool/update_chart.py:update_chart. Its request defaults to preview; a persistence experiment must set generate_preview=False. The code performs chart lookup, dataset access checking, normalization, compile validation and a save path. Mocking those into success would not qualify as a real-storage replay. The existing chart-utils unit tests alone cannot establish persisted state loss.

Relevant source paths inspected at the final repair: update_chart.py, generate_chart.py, chart/compile.py, pyproject.toml, requirements/development.txt and tests/conftest.py. Dependencies are extensive; Python >=3.11 and local superset-core are required. Do not install locally given storage constraints. An attempted listing of tests/integration_tests/mcp_service did not yield usable content; this is not proof that integration coverage is absent.

Next: inspect real database/app fixture setup and the save path, establish a bounded synthetic dataset plus real Slice persistence, then register the application protocol and source pins before dispatch. Needed controls include explicit defaults/null and a visualization switch. Dataset rebind semantics require special care: update_chart can deliberately preserve valid inherited fields even though the lower-level merge helper's dataset_rebind flag resets presentation. A helper-only test must not be described as the full production path.

No CI application run has been dispatched for Superset. No extra paid calls were made.
