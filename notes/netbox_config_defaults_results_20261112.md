# Completed NetBox configuration-default calibration

Corrected run 43157153410 succeeded for both adjacent NetBox versions at study commit a0561075828ce8663235c0291b59a55133b8b1ad. All 24 registered cases executed and qualified. This is reproduction of known issue 18669, not a new defect discovery.

| Version | Cases | Successful creation/readback | Configuration violations |
| --- | ---: | ---: | ---: |
| Faulty parent cac41cd0 | 12 | 12 | 6 |
| Fix c108c738 | 12 | 12 | 0 |

In both default configurations, an empty custom-field map, a sibling-only map, and a partial override omitted expected defaults on the faulty version. The API represented the affected values as null, while database inspection showed absent keys. Response and readback consistently reflected that loss. The fixed version persisted the configured values. Omitting the entire custom-field map worked on both versions. Explicit overrides and explicit null/false/zero passed on both versions.

The second configuration changed text alpha to beta, Boolean true to false, and integer 7 to 0. Expectations followed API-retrieved configuration. This checks configuration binding and falsy-value handling. It does not demonstrate discovery of the relevant metadata endpoint or automatic inference of default precedence.

## What this establishes

A configuration-derived check can distinguish this historical faulty/fixed pair while a success-status check passes every case. The 24 cases are correlated variants of one defect, not 24 independent samples or six distinct defects. No significance test, general false-positive estimate, model ranking, or current vulnerability claim is warranted.

The implementation uses the real REST handlers through Django APIClient, authenticated as a disposable superuser, with actual PostgreSQL and Redis. It does not exercise network transport or the authentication handshake. The semantic template is handwritten using the exposed historical requirement and fix. An equally informed handwritten checker is a strong reference and would have access to the same expected values. The result does not establish superiority over existing semantic API testing methods.

## Attempts, environment and cost

Attempt 1, run 43156734009, failed to build the pinned psycopg-c driver on both application pins before scientific execution. It used 2.3167 application-job minutes. Both failures and all logs are retained.

The sole registered correction used the official prebuilt psycopg-binary package at the same version, 3.2.6, instead of compiling the C extra. Both versions used that corrected environment. Upstream source and original requirements were unchanged; the separate replay requirements and resolved packages are archived. This is not an exact reproduction of an unspecified original deployment environment.

Attempt 2 used 7.5667 application-job minutes. Total across both attempts: 9.8833 application-job minutes, excluding separate unit-verification jobs and queue time. Paid model calls: zero. These durations are execution accounting, not an account billing statement.

## Reproduction

```
python scripts/extension/verify_netbox_config_defaults_v1.py --archive results/netbox-config-defaults-v1-ci-43156734009 --output manifests/netbox-config-defaults-attempt1-v1.json --verify
python scripts/extension/verify_netbox_config_defaults_v1.py --corrected --archive results/netbox-config-defaults-v2-ci-43157153410 --output manifests/netbox-config-defaults-results-v2.json --verify
```

The manifests hash every archived file. The verifier reconstructs expectations independently, checks explicit-value types and omitted keys, links observations to raw API requests and resource IDs, and verifies registration, application commits, instrumentation and the exact dependency overlay. The `historical_faults` field in these calibration manifests denotes the one targeted known issue; attempt 1 has zero runtime-qualified observations.

## Research decision

Feasibility passes for this particular oracle-source mechanism. Broad efficacy, automatic extraction and Q1 submission readiness remain unestablished. Configuration-dependent testing and stateful REST metamorphic testing have prior art; see configuration_oracle_prior_art_20261112.md. Do not expand the six variants into an apparent sample of independent bugs or extend this application's matrix merely to increase counts.

The next substantive gate is cross-project applicability of a reusable metadata-to-contract mapping, with explicit overrides and null semantics preserved, against an information-matched reference. A generic default-name heuristic is insufficient. Before new application runs, define the mapping and project selection, verify each project's semantics, and establish that the task differs materially from existing configuration-based testing. Preserve projects for which metadata is missing, ambiguous, or already sufficient for an existing baseline. A failed novelty gate ends this candidate rather than triggering a larger matrix.
