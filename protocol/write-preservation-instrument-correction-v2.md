# Instrument-only correction, 2026-11-11

Run 43079402952 failed compilation in both versions with SQLx 0.9 error E0277: a dynamic String cannot be passed directly to query_scalar. No test body executed and no scientific observations exist. Both reports and build logs are retained in results/write-preservation-calibration-v1-ci-43079402952.

Version 2 uses the documented SQLx QueryBuilder to execute the identical SELECT assembled from quoted column names returned by PRAGMA table_info. There is no application-supplied SQL or value interpolation. Source: https://docs.rs/sqlx/0.9.0/sqlx/struct.QueryBuilder.html (new and build_query_scalar).

The upstream commits, three cases, two channels, raw-state scope, write set, input JSON, scoring and stopping rules remain unchanged. The v1 Rust source, runner, workflow and registry remain immutable. The v2 registry hashes the correction files, predecessor registry and every retained failed-attempt file. This consumes the one allowed correction dispatch. A subsequent failure stops this calibration for review rather than authorizing another retry.

Both first-attempt runners reported Rust 1.99.1. Dependencies resolved from Cargo.lock under --locked. The correction remains a historical, outcome-exposed development calibration, not an independent efficacy experiment.
