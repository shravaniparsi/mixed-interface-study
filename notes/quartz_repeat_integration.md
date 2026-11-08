# Quartz repeat-dispatch integration qualification

Hosted application run [42527108389](https://github.com/shravaniparsi/mixed-interface-study/actions/runs/42527108389) passed at executing commit `dfcf704dc973f59c9f2a86bcc9101cad564e5dfb`. Unit run 42527085645 passed all 359 harness tests: 290 Python, six bootstrap and 63 Node.

The new controls-only campaign entry point executed two planned pairs and four independently initialized branches. It translated each pair's raw records into the repeat planner's outcome contract and correctly scheduled zero follow-up jobs. Local independent verification reproduced the source checks, pair extraction, dispatch records and final campaign ledger. All four branch cleanup records confirmed application-port release and browser absence. The branch durations summed to 69.144381181 seconds; these are operational measurements, not selector calibration.

Fifteen new Python integration tests and six Node dispatch tests cover intent-before-launch ordering, stop behavior, flagged follow-up order, rejected prefixes, policy-only failures, shared and assigned failures, control/mutation separation and malformed pair selections. Flagged follow-ups were exercised with synthetic executor outcomes, not real application failures. The live controls establish the normal dispatch/extraction path only.

The [qualification manifest](../manifests/quartz-repeat-integration-qualification.json) pins 55 compact evidence files. Full downloaded logs and browser screenshots remain in the working artifact directory. The historical runner, adapter, component reducer and previously archived results remain unchanged.

The forty Quartz mutation branches remain unexecuted. Next, qualify the new pair-dispatch path's interruption/deadline behavior and subsequent fresh controls, then finish the negative-outcome and primary-environment freeze checks. Boundary execution remains outside this controls-only entry point. Repeated controls are not independent samples, and source-check discrepancies are not adjudicated defects.
