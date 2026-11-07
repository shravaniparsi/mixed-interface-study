# Source-qualified observation extraction

RealWorld and PetClinic now have read-only component reducers tied to their archived executing-source and registry versions. They separate immediate producer observations, assigned continuation actions, shared API readback, supplementary UI verification, execution integrity and unresolved policy. The original evidence is unchanged. These reducers recover observations; they do not assign new defects or independent root causes.

| Retained evidence stratum | Records inspected | Qualified for bounded extraction | Incomplete |
| --- | ---: | ---: | ---: |
| RealWorld main development | 50 | 49 | 1 |
| RealWorld diagnostic repeats | 16 | 14 | 2 |
| RealWorld Mac generated validation | 18 | 17 | 1 |
| RealWorld hosted generated validation | 18 | 18 | 0 |
| PetClinic main development | 36 | 36 | 0 |
| PetClinic diagnostic repeats | 6 | 6 | 0 |

The 144 records include overlapping workloads, repeated cases and different environments; they are not 144 independent samples. Qualification means the available records satisfy the reducer's source-specific extraction checks. It does not establish primary-runtime readiness or supply missing process evidence. [Machine-readable extraction summary](../results/oracle-extraction-20261107/summary.json).

Four historical RealWorld records retain `capture_error` events when a browser context closed before response-body capture completed. They remain incomplete. These are evidence-capture problems, not newly identified application faults. The hosted validation stratum separately qualifies all 18 records; its timing is not pooled with the Mac run. Future capture shutdown needs repair before primary execution, and original incomplete records must remain preserved.

PetClinic extraction distinguishes four recorded 500 responses across two candidate pairs from validation rejections. It preserves the known hyphenated-name native submission block and the two whitespace-policy blocks separately. These reproduce earlier development observations. A mismatched direct API edit payload invalidates comparator parity; a native payload discrepancy remains a native observation requiring adjudication. Producer-field checks using only the response belong to the immediate-response component, while persisted graphs and shared readbacks remain separate.

Recorded PetClinic fields and requests support retrospective audits of loaded date/owner values, request payloads and owner–pet–visit preservation. No pre-candidate snapshot exists after pet/visit setup, and no per-branch exit or owned-browser-cleanup confirmation was recorded. The reducer reports those limits rather than constructing missing evidence. Future executing adapters still need the corresponding guards and bounded cleanup.

The Quartz paired-control wrapper now saves a hashed source/input/environment plan before dispatch, permits exactly the four existing controls once each, and validates two independently reset prefix pairs. [Its prospective control protocol](../protocol/paired-control-validation-v1.md) fixes ordering, timeout handling and invalid-attempt policy. The scope contains no mutation cases and does not implement a primary multiworkflow or selector campaign.

Local validation and [hosted unit run 42356470965](https://github.com/shravaniparsi/mixed-interface-study/actions/runs/42356470965) passed 157 Python harness tests, six CI bootstrap/context tests and nine Node tests, 172 in total. CI also verified the preparation hashes and declared pair inventory.

The [hosted paired-control run 42356532879](https://github.com/shravaniparsi/mixed-interface-study/actions/runs/42356532879) completed at source commit `a5a91d35ba1f82de4fa3c3caa33ed7819e50597e`. It ran API/API, API/UI, UI/UI and UI/API in the saved order, using four fresh JVMs. Both pairs passed all 17 comparability checks: actors, initial and accepted-prefix states, registered producer inputs, returned-state bindings and actual consumer payloads agreed. All 62 recorded branch checks passed; worker exits, Java/browser cleanup and released ports were confirmed for all four branches. Source/input hashes and effective options matched the pre-dispatch plan. The campaign completed normally in 59.318 seconds, without timeout or interruption. This is recorded execution time, not a speed comparison or deadline-path test.

[Compact evidence and provenance](../manifests/quartz-paired-control-validation.json) are tracked in Git; the full downloaded artifacts remain in `results/ci-runs/42356532879`. Hosted artifact expiry is 14 November 2026, so the local copy must be retained until a durable archive is established. Read-only agent review independently checked the underlying requests, state hashes and cleanup records; it is not human adjudication. These two ordinary control pairs validate the paired runner for one workflow. All 40 Quartz boundary cases remain unexecuted.

The eight-workflow primary freeze remains incomplete. Next work is to repair future RealWorld response capture during shutdown, add the executing adapters' payload/binding and rejected-prefix state guards, and extend paired replay and runtime qualification across the retained workflows. Historical incomplete records stay unchanged.
