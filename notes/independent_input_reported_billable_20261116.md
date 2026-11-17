# Independent-input GitHub billable execution

The GitHub timing endpoint reports zero billable milliseconds for all 14 runs and 39 jobs in the existing independent-input cost ledger, including failed qualification. The captured job IDs match that ledger exactly. These run IDs are disjoint from the 17-run, 31-job benchmark billing audit: together the two scopes cover 31 runs and 70 jobs with zero reported billable execution time.

This is provider-reported run timing, not a whole-account invoice or a claim that storage, subscriptions, repository checks, earlier studies or external services have no charges. It does not replace the elapsed-time reports or change scientific results. The endpoint responses and collection timestamp are retained in results/independent-input-actions-billable-v1 and manifests/independent-input-actions-billable-v1.json.

Reconstruct with python3 scripts/extension/verify_independent_billable_v1.py. The verifier checks hashes, job identity, run uniqueness, timing arithmetic and disjointness from the benchmark run set. No new application or model experiment was run for this audit.
