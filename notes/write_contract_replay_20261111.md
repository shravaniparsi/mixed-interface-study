# Portable manual-contract replay

The same application-independent checker now replays the 36 existing Tiller/Iris records and eight Fast Dash observations. No application was rerun. These 44 historical records are separate from the independent-input study's coincidentally equal count of 44 paired executions.

| Check | Alerting records | Coverage |
|---|---:|---|
| Advertised input schema | 0 | 44 |
| Operation reports success | 0 | 44 |
| Requested assignment persists | 0 | 44 |
| Unrequested, non-derived state changes | 5 | 44 |
| Expected derived assignment fails | 2 | Four Fast Dash records with a derived-clear obligation; two fail |
| State/readback/invocation-argument agreement | 1 | Eight Fast Dash records only |
| Union of contract alerts | 7 | Overlapping checks; not seven independent defects |

Four Tiller manifestations, one Iris manifestation and two Fast Dash parent-change observations comprise the seven alerts. The Fast Dash fixed parent-change observation fails both the derived-assignment and agreement checks, so their totals cannot be added. The pinned repair removes the child key while readback advertises null; the callback invocation omits that argument. The historical parent-change observation retains a child value invalidated by the parent change. A generic preservation-only rule cannot express both obligations correctly.

All six Fast Dash non-target controls and all eight Iris intentional clears remain unflagged. Tiller explicit-empty-note historical cases remain flagged for collateral ordering loss, not for the intended empty note. The checker treats missing keys as different from explicit null, and booleans as different from numbers. Missing measurements are unavailable; two measured views both omitting a required field fail agreement.

## Reuse interface

`src/mixed_interface/write_contract.py` has no application names, callback-specific rendering, or outcome labels. Each record supplies before/after objects, requested assignments, permitted derived fields, optional expected derived values, measured views and explicit equality obligations between those views. The exporter still contains application-specific mappings, including the manual Fast Dash cascade contract and correspondence between state keys and invocation arguments. This moves representation into data; it does not eliminate specification work.

Run the standalone consumer, requiring only the Python standard library:

```sh
PYTHONPATH=src python3 -m mixed_interface.write_contract \
  manifests/write-contract-replay-v1.json --output /tmp/replayed-scores.json
```

Reconstruct and verify provenance separately:

```sh
python3 scripts/extension/build_write_contract_replay_v1.py --verify
```

The consumer's complete score list was compared with the stored reconstruction. Seven unit tests cover legitimate cascades, stale values, missing versus null, unmeasured views, jointly missing required keys, boolean/number distinctions and overlapping requested/derived assignments. These are checker correctness tests, not additional application evidence. The original application-specific verifiers remain responsible for source, fixture and execution qualification.

## Contribution implication

The artifact now demonstrates a common replay interface across target-row preservation and process-state/continuation checks. A complete manually supplied contract catches the observations, so this result strengthens the competent baseline. It does not establish a novel method, automatic contract inference, reduced human effort, independently measured diagnostic accuracy, unseen-project transfer or current-release defects. External researcher reuse has not been tested. The closed-cohort contribution assessment and its Q1-readiness decision are unchanged.

The next method comparison must give baselines these same state observations and distinguish a method's inferred obligations from manual ground truth. Comparing a fully annotated proposed method against only schema validation would not demonstrate the required advance.
