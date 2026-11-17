# GitHub-reported billable execution audit

Read-only GitHub run-timing queries were collected for all 17 archived benchmark runs. The responses report zero billable milliseconds for all 31 Ubuntu jobs. The verifier binds each returned job ID to the retained terminal metadata; no job is silently omitted or counted twice. The latest scientific run's response reports real run duration separately from zero billable execution time. Thus zero here does not mean the experiments did not run.

This is stronger evidence than inferring free execution solely from repository visibility. It supports zero GitHub-reported billable execution time for this explicit benchmark scope. It does not establish a zero-dollar whole-project invoice: artifact storage, unit workflows, other research stages, subscriptions and external services are outside these responses. Historical elapsed-job cost snapshots remain unchanged.

Raw endpoint: /repos/shravaniparsi/mixed-interface-study/actions/runs/{run_id}/timing. The collection timestamp and exact run IDs are retained in results/benchmark-actions-billable-v1/collection.json. Raw responses are hashed in manifests/benchmark-actions-billable-v1.json. Reconstruct using scripts/extension/verify_benchmark_billable_v1.py --verify.

No paid service, application rerun, or model call was initiated. This audit closes the benchmark execution-billing metadata gap, not the scientific contribution gap. The Q1-readiness assessment is unchanged.
