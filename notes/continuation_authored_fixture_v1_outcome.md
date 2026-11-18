# Authored browser observation qualification outcome

Run 44371691916 completed successfully at the published fixture freeze
820ae95366a1e812ea9fdefce04cf7fc5b422358. All nine authored outcomes matched their
prespecified labels. The retained-evidence verifier separately checks the frozen
inputs, run identity, case order, requests/statuses, saved records, missing
observations and write-contract results. No application rerun was used to verify
these observations.

Native ordinary creation and API ordinary creation both supported an ordinary
Description edit. The null producer was rejected in the rejection fixture,
normalized in the normalization fixture, and persisted unchanged in the blocking
fixture. In the last case the ordinary Save click caused one invalid event and
zero native POSTs during the fixed 500-ms window; the stored record stayed
unchanged. This is an engineered blocking example, not a naturally discovered
frontend/API defect.

The removed-actor case produced 401 before editing. The competing-version case
produced 409 and retained only the prespecified version increment. The extra-write
case returned 200 but changed Title as well as Description; the existing
write-contract baseline detected the Title frame violation. The readback-outage
case actually saved its edit but remained observation_unavailable because both
API readbacks returned 503. File ground truth did not fill the unavailable
measurement channel.

The Python baseline pass used write_observations_v2 and write_contract. Its four
applicable successful-write frame checks passed for native ordinary, API ordinary
and normalization, and detected the deliberately injected extra write. Restart
persistence and native continuation remain explicitly unmeasured in the generic
persistence baseline; the browser observations are separate evidence.

Runtime: Node v20.20.2, Chromium 151.0.7922.34 from locked Playwright 1.62.1. The
job reported 252 seconds of run duration and zero Ubuntu billable milliseconds.
That covers only this development job, not the entire project. The only local
execution before publication was syntax/context checking; the browser fixture
ran on a standard GitHub-hosted runner.

This result qualifies this small authored observation path. It does not qualify
real-system deployment, full state restoration, a universal 500-ms blocking
oracle, counterfactual JSON materialization, source-aware baseline superiority,
independent sampling or a publication contribution. The catalog remains closed
with zero scientific cases. Nine correlated authored controls are not nine
independent defects.

Reproduce evidence verification without running an application:

    PYTHONDONTWRITEBYTECODE=1 python3 scripts/extension/verify_authored_continuation_fixture_v1.py

The next method gate is demonstrating comparable starting state and a prescheduled
causal intervention without suppressing unintended writes or normalization. Any
additional fixture version must be published prospectively; this successful run
is not permission to retry failed real projects or search another cohort for
positive findings.
