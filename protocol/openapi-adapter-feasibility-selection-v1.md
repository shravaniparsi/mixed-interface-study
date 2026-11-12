# Independent-input adapter feasibility: selection gate v1

## Question and contribution boundary

Can the same source-defined write operation and schema-valid argument be executed through current off-the-shelf OpenAPI-to-MCP converters without changing its persisted effect? This is a candidate comparative empirical study, not a claim to invent differential testing, MCP conformance, state verification, or semantic-preservation testing. AutoMCP already reports follow-up state queries for writes. Existing public work also addresses MCP lifecycle behavior and OpenAPI-to-MCP response semantics.

This gate does not replace, reopen or enlarge the closed independent-input native/API cohort. It does not yet authorize scientific application execution. A frozen source fixture, complete input inventory, competent baselines and bounded runner registration must precede runtime observations.

## Fixed capability-selected subjects

Select exactly PrefectHQ/fastmcp, punkpeye/fastmcp and ivo-toby/mcp-openapi-server. Public capability descriptions identify direct OpenAPI-to-MCP conversion; the sample spans Python and TypeScript implementations. This is a purposive feasibility sample, not an ecosystem census or prevalence sample. Use the latest non-prerelease GitHub release identified at selection time, with its exact resolved commit; do not switch releases based on yield. Retain unavailable or unsupported subjects with reasons; no replacements.

Pins are retained in results/openapi-adapter-feasibility-selection-v1/release-pins.json. Release identities and capability descriptions were inspected; pinned implementation bodies and our own runtime outcomes were not. Researchers have prior knowledge of omission/null problems in other MCP products and public semantic-preservation work. The sample is not fully blind or an untouched ecosystem holdout. The five issue-derived leads in adapter_semantics_search_exposure_20261112.md are not selected cases.

## Input and workflow construction constraints

Construct inputs from a separately authored source API contract before inspecting converter implementations or generated schemas. Cover two explicitly different operation semantics: creation with server-side defaults, and partial updates that preserve absent members but distinguish explicit null, false, zero, empty strings, ordered arrays and nested objects. Specify clear/removal behavior explicitly rather than inferring it from nullable types. Avoid an inconsistent contract that declares client-side defaults while demanding omission-preserving updates.

The source fixture is synthetic and controlled. It provides a deterministic reference, not a sample of real application bugs. Source-API inputs must satisfy the source schema. Generated MCP schemas are observations: do not prune source-valid cases simply because a converter narrows the representable domain. Record tool-schema rejection, unsupported operation/media type, translation/runtime failure and complete execution separately. Freeze the ordinary-value qualification cases as well as all scientific input cases before outcome inspection.

Define bindings from source operation/parameter identities to generated tool arguments using public interface contracts and discovery output. Record ambiguous or impossible bindings; do not use knowledge of observed failures to repair mappings. No arbitrary string-equality comparison of normalized wire data may be equated automatically with a semantic defect.

## Competent comparisons required before execution

1. Source and advertised-tool schema validation, with both validity judgments retained.
2. Direct REST execution under identical fresh initial state and actor context.
3. Captured outbound request comparison, preserving absent/null/type/array distinctions while permitting declared encoding equivalences.
4. Handwritten source-semantics reference for persisted state, shared by both routes. This is not independent learned ground truth.

State comparison may establish consequences of request differences; it is not automatically a new detection method beyond a complete request comparator. Benign request differences, unsupported cases and startup failures remain visible. No LLM-agent performance or user-intent inference is measured.

## Gate, bounds and stopping

Before any scientific dispatch, freeze the exact source contract, case enumeration, qualification controls, expected effects, binding policy, dependencies, artifact requirements and workflow hashes. Maximum preliminary envelope: three initial application jobs of 15 minutes; at most one separately documented infrastructure correction per subject of 15 minutes. Aggregate ceiling 90 application-job minutes, zero paid model calls, within the existing $100 cash ceiling. No paid infrastructure is provisioned. These are ceilings for a subsequent registered runner, not an execution authorization from this document alone.

No finding-driven repetitions, version substitutions, case additions or application patches. A failure to qualify ends that subject after its allowed correction. Positive, null and unsupported results all inform feasibility. Cases within the same converter and operation family are correlated; faults require source-level deduplication and cannot be counted from variant totals.

A complete pilot would establish measurement feasibility only. A defensible larger contribution still requires verified differentiation from prior work, independent real-workflow evidence, a justified sampling frame and meaningful incremental empirical knowledge. If these are absent, stop rather than rebrand a conformance demonstration as Q1 readiness.
