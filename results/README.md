# Evidence in this repository

Git tracks the reviewed compact summaries and development tables explicitly listed in `.gitignore`. Full per-case requests, screenshots, process records, logs and execution-source snapshots remain in the original research workspace under this `results/` directory. They are excluded from Git; no raw evidence was deleted to prepare the repository.

The historical evidence is not fully reproduced by a source checkout alone. In particular, `scripts/summarize_development_batch.py` and `scripts/summarize_runtime_integration.py` validate underlying case files and require the complete corresponding local run directory. The tracked summaries, source hashes, evidence indices and attempt-status records identify their provenance; they are not substitutes for the underlying observations.

A fresh checkout can run the test suite, regenerate the registered candidate pools, and execute new local or GitHub Actions runs using the documented setup. CI uploads the newly generated evidence as a run-specific artifact. Artifact retention is finite; retained research data must be exported before expiration. No public data archive or complete historical raw-data upload is claimed at this stage.

The current complete local evidence remains in `outputs/mixed-interface-study/results/` in the original Codex workspace. Existing detailed indices include `manifests/quartz-evidence-index.json` and `manifests/petclinic-boundary-evidence-index.json`. Historical platform paths are retained as provenance in this private repository; a future public release needs a separate export review.
