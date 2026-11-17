# Oracle-acquisition scoring infrastructure

Read the saved baseline helper implementation at revision 60de49d135fd419ef8a2e93357c025eee154e4c6. Its helper functions distinguish satisfied, mismatched, unknown and code error. No generated code, baseline artifact, service or model was executed. The source evidence is the existing hashed constraints_test_generation.py file; helper sections are now inspected in addition to previously recorded entrypoints.

Implemented fixed-frame paired scoring in src/mixed_interface/oracle_acquisition.py with explicit unknown/error/not-run states, independent unresolved-label accounting, per-project summaries and paired verdict retention. Missing predictions and duplicates fail validation. Ratio denominators preserve abstentions, and undefined ratios remain null. The baseline label mapping is only a vocabulary adapter, not a working or validated RBCTest implementation.

Seven engineering checks pass: retained abstentions/unresolved labels; missing/duplicate predictions; all-abstaining methods; required label evidence; invalid verdicts; absent positive cases; and baseline unknown/error translation. These examples are synthetic engineering fixtures, not new research observations or a baseline performance comparison. Preparation hashes and diff checks passed after integration.

The scorer closes a measurement-definition task. It does not close the remaining scientific gates: an implemented differentiated method, independent task/constraint sampling, correct externally justified labels, a qualified information-matched baseline, and bounded execution. The project has not collected a new cohort or measured oracle acquisition accuracy/cost savings. No paid compute or model calls occurred.
