# Normalization and execution-cost scope v1

The normalization manifest and executable expectation helpers describe the pinned RealWorld implementation. They are not independent requirements and do not establish defects. Historical runners and reports retain their original predicates. The new rules must be integrated and validated in the prospective paired runner before its freeze.

## Separate commands, state and representations

Compare actual submitted commands as JSON values without coercion. Object property order is immaterial. Array order, duplicates, omission, explicit null and empty strings remain distinct. Do not trim registered inputs, replace null with baseline values or insert missing required values to make a native submission succeed.

For RealWorld article tags, compare unique-string membership for semantic state while retaining a separate response-representation check: the pinned serializer emits sorted, unique values. Sorting or deduplicating the observed response must not erase a representation discrepancy. Omitted create tags predict an empty list; omitted update tags preserve prior membership; an explicit empty list clears tags. Null tags are not an empty-list default. Preserve case and whitespace. The native add-tag control trims new input; a whitespace-tag candidate therefore needs explicit representation/parity adjudication, not silent harness trimming.

For profile bio/image updates, omission preserves the previous value, whereas explicit null or empty strings predict null output. Unedited null settings fields are omitted by the native submit handler. This is a request-construction rule, not permission to equate arbitrary omitted/null commands. Username, email, password and explicit-null partial article updates require separate rules and remain outside these helpers. PetClinic and Quartz acquire no new implicit normalization from this change.

The retrospective control audit predicts only the registered RealWorld article-create, body-update and bio/image profile projections. It retains comments as outside scope and rejected prefixes as having no accepted-state expectation. It does not replace the unified control analysis or add samples. Synthetic ordering, duplication, missing/null and whitespace tests are software tests, not application experiments.

## Primary diagnostic timing boundaries

Record a monotonic clock origin and actual wall time per independently reset branch. The branch interval starts before its reset and ends after evidence capture and confirmed owned-process teardown. It includes backend startup, authentication, browser/context startup, producer work, the assigned continuation, shared verification and cleanup. Failed and timed-out attempts retain all elapsed work and contribute to attempted-work denominators. Late completion cannot earn feedback credit.

Report checkout, dependency installation, application build, shared fixture construction and shared frontend startup as common setup outside the branch interval, with their own elapsed totals. Do not silently allocate setup differently by continuation channel or strategy. If a later deployment charges setup to a budget, register that alternative scope before timing and apply it identically to every method.

Use mutually exclusive top-level intervals for reset/startup, authentication/session setup, producer, assigned continuation, shared verification, evidence finalization and teardown. Asynchronous capture that overlaps an operation remains inside that operation's wall time; only final drain/persistence has a separate exclusive interval. Report overlapping subspans separately without adding them to the exclusive total. Preserve uninstrumented gaps explicitly; never assign an unexplained residual to an allegedly pure API or UI cost. Cross-process timestamps require an explicit monotonic origin/offset scheme or should remain separate spans.

The first diagnostic comparison is equal-candidate, not equal-budget. Report end-to-end branch costs separately from assigned-action costs. Existing combined phases and the 221.313-second interruption qualification are not selector calibration. The later selector experiment retains a common wall-time budget, fault-label-free valid-control calibration, the same effective pool and costs for all methods, and explicit deadline/overrun accounting.

Implementation status: existing controllers record some end-to-end costs, but common exclusive phase instrumentation across all retained workflows is incomplete. This document fixes the cost contract; it does not claim that missing timing measurements exist. Primary freeze remains incomplete until prospective normalization integration, phase instrumentation and the remaining runtime/schedule checks pass.
