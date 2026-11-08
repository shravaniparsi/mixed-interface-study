# Terminal outcomes, version 2

Status: implemented common contract and fixture-qualified driver; application integration pending. This prospective contract does not change archived version 1 evidence or authorize primary boundary execution.

A terminal record separates the observed application behavior from permission to dispatch another job. Every record carries a version, policy digest, immutable job identity, the retained observation, and SHA-256 references to supporting artifacts. Artifact hashes establish identity, not evidential sufficiency: application-specific loaders must verify source, selection, environment, trace and cleanup before constructing a record.

| Terminal kind | Initial sweep | Two candidate repeats, each with reference control | Complete semantic evidence |
|---|---|---|---|
| clean_observation | Continue | No | Yes |
| completed_mismatch | Continue | Yes | Yes |
| matched_rejection | Continue | No | Yes |
| unresolved_policy | Continue | No | No |
| application_response_failure | Continue | Yes | No |
| incomparable_observation | Continue | Yes | No |
| missing_evidence | Halt | No | No |
| case_timeout | Halt | No | No |
| environment_failure | Halt | No | No |
| cleanup_unconfirmed | Halt | No | No |
| interrupted | Halt | No | No |

The same decision function governs the driver and planner. Timeouts halt even when cleanup succeeds: they do not establish an application response and may indicate exhausted resources. This explicitly replaces version 1's broad rule scheduling every incomplete record, for version 2 campaigns only. A later successful campaign cannot replace a halted attempt.

Precedence for an application bridge is: unconfirmed cleanup; interruption or timeout; invalid environment/source/selection; missing required evidence; supported application response failure; incomparable observations; complete diagnostic mismatch; unresolved policy; matched rejection; clean accepted observation. Multiple reasons remain in supporting evidence even when one terminal kind determines dispatch. An HTTP error alone does not qualify as an application response failure. The bridge must identify the registered request and phase in the trace, confirm the expected actor and initial state, and distinguish authentication/reset failures from failures after the candidate starts. Unknown or unsupported evidence must halt.

An unresolved policy label cannot suppress a requirement-check mismatch. A matched rejection requires comparable complete evidence, no requirement mismatch, and the workflow's required rejected-state checks. Neither supplies a fabricated downstream continuation outcome. Shared readback failures receive no channel-exclusive credit.

The initial sweep must finish before repeats are planned. The schedule remains candidate repetition 2, matched reference repetition 2, candidate repetition 3, matched reference repetition 3. Initial observations and every repeated attempt remain in the record. Repeated failures do not create recursive repeats. Any halt stops the next dispatch immediately. A checkpoint records intent before launching each job; failed checkpoints prevent launch. Executor exceptions retain the started-job identity and propagate.

Repeat summaries retain terminal kinds and variability. All three candidate observations and all three controls must have complete semantic evidence before reporting stable observations. Controls must be clean accepted observations. Repeated application response failures or incomparable observations remain unresolved even if their signatures match. Stability is not defect adjudication; independent sample size remains unset.

## Qualification and remaining integration

`terminal_outcomes.py` and `campaign_v2.py` are separate from the source-pinned version 1 implementations. Tests cover every terminal class, planner/driver agreement, halt during repeats, immutable job identity, policy hashes, incomplete sweeps, failed checkpoints, interruption, control failures and a bounded subprocess transport experiment. The transport experiment emits synthetic records, exits nonzero on application-failure fixtures and verifies retention and the fixed follow-up order. It does not run Quartz, RealWorld or PetClinic and does not validate their negative-outcome extraction.

P1 remains open until source-qualified application extraction and launchers consume this contract. In particular, the current Quartz adapter exits 1 when an application read fails; the pair runner rewrites that to `child_exit_error` and stops before the other branch; the campaign wrapper raises before extracting it. A new versioned runner/bridge must preserve the raw observation, decide whether it is a supported application response failure, and finish the paired observation only when runtime integrity permits. Simply removing the wrapper's exit-code check would be insufficient. Use source-shaped negative fixtures and declared engineering controls to qualify that change before any untouched boundaries. RealWorld and PetClinic bindings remain part of P2.
