# PetClinic terminal integration

The six previously exposed engineering controls completed through immutable per-job dispatch in application run [42556695482](https://github.com/shravaniparsi/mixed-interface-study/actions/runs/42556695482), source commit `c9b1b4d71fda1bbfa5dfb8c470f69b7c0f414566`. Unit run 42556674225 passed 523 tests.

The run contains six pairs and twelve independently reset branches across owner, pet and visit workflows. Three pairs completed accepted continuations and three pairs produced matched 400 rejections with readable unchanged state. Consumer order alternated across the six jobs. No followup jobs were triggered. Independent replay verifies the source snapshots, immutable jobs, raw branch bindings, extraction, cleanup, and full campaign ledger.

The compact archive retains JSON observations and source snapshots. Build logs, process logs and screenshots remain in the downloaded full artifact under `work/petclinic-terminal-ci-42556695482`; they are not inputs to the compact replay. The qualification manifest hashes every retained compact file.

This qualifies the selected 201/400 control paths. Unexpected prefix outcomes, the other twelve PetClinic candidates, remaining RealWorld bindings, bounded primary batches, common cost accounting and final freeze remain open. Synthetic blocked-UI and changed-rejection fixtures validate extractor behavior, not additional application findings. No untouched boundaries ran, and these controls do not add independent scientific samples.
