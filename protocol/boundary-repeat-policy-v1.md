# Boundary repeat policy v1

Status: executable planning and synthetic verification. This policy does not qualify an application runner or authorize primary execution. The Quartz preparation retains all 22 inventory pairs, including two ordinary controls and 20 mutation pairs whose 40 branches remain unexecuted.

## Schedule and reference controls

The initial sweep uses the pinned pair-inventory order, alternating API→UI and UI→API between pairs. Each branch requires an independent reset and prefix replay. A reference must be the unique registered unmutated route-only control for the same workflow and producer interface. A UI-producer control cannot substitute for an API-producer control. Reference selection is fixed before outcomes exist.

After a terminal outcome for every initial pair, flag channel discrepancies, any registered check failure (including shared and immediate checks), mixed prefix outcomes, and incomplete executions. Clean matched rejections do not create downstream failures. These signals schedule investigation; they are not adjudicated requirement violations. An unresolved policy alone is not an execution failure.

For each flagged pair in initial order, schedule candidate attempt 2, its reference control, candidate attempt 3, and its reference control. Each job contains both independently reset continuation branches. Thus each flagged pair adds eight branch slots: four candidate repeats and four control branches. The continuation order for a given pair remains its registered initial order. Controls shared by multiple flagged candidates are repeated alongside each candidate; their observations are not reused as independent samples.

## Failure, stop and evidence handling

Unknown fields, missing diagnostics, duplicate/foreign/reordered job IDs, altered plan semantics and ambiguous reference controls fail validation. A complete outcome requires an explicit prefix classification and nonempty source-qualified observation signature. Incomplete outcomes retain missing diagnostic flags and partial signatures. Applications must supply these records through a qualified extractor; a successful process exit is insufficient.

A partial initial sweep or unconfirmed cleanup halts planning. No resume, overwrite, automatic replacement or cross-attempt merging is permitted. A corrected campaign needs a new complete attempt with new evidence paths, retaining the old attempt. A terminal incomplete pair with confirmed cleanup may enter the diagnostic repeat schedule after the complete sweep. Actual launchers must enforce cleanup and stop conditions; the pure planner does not stop processes.

The outcome signature must preserve relevant prefix and component outcomes under the workflow's frozen normalization rules. Stable outcomes require all three candidate attempts to be complete, cleanup confirmed, the initial reference control and both accompanying controls to pass, and candidate signatures to agree. Different signatures report variability; missing repeats, incomplete execution and failed reference controls remain explicit. All observations remain available regardless of classification. Stability does not establish a defect, root cause, or independent replication.

## Implementation boundary

The pure repetition module builds and hashes plans, chooses follow-ups and summarizes supplied outcomes. The Quartz preparation script pins the inventory and code, emits the 44-slot initial schedule and exercises synthetic scenarios. It never launches applications. Integration with boundary-capable adapters, qualified extraction of negative outcomes, deadlines, broader cleanup checks and final environment freeze remain required. Synthetic outcomes are labeled and excluded from experimental results and denominators.
