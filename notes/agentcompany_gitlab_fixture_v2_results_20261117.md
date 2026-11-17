# Namespace GitLab diagnostic closeout

Run 44060852176 at frozen head 9605741a406bb5e70e38ffa116ad7d27bff0c550 is terminal and closed. Job 133962056069 took 885 seconds and its matching GitHub timing response reports zero billable execution milliseconds. Cleanup of the container, anonymous volumes and internal network succeeded. No authenticated API request, token inspection, task setup, fixture query or scientific case occurred.

## Observed sequence

The immutable image pulled and the new container initially ran with PID 2460. Its network namespace was net:[4026532757], matching the namespace reported by the first HTTP client. That health GET received URLError with errno 111, connection refused. This confirms the client entered the registered namespace; it does not establish a working HTTP endpoint.

The container started at 10:05:40.949542232Z and exited at 10:05:51.536720792Z, roughly 10.6 seconds later, with exit code 1 and OOMKilled=false. The retained reconfiguration log reports gitlab-workhorse restart failure: runsv not running. The service-status command subsequently reported that the container was not running. The underlying cause of the supervision failure is unresolved; no race, Docker defect or application validation bug is confirmed.

After the exit, 39 subsequent loop iterations failed the PID guard before making a request. The artifact has 40 readiness loop records but only one actual health HTTP attempt. The guard prevented requests from running in a changed namespace. The outer readiness loop nevertheless waited until its deadline instead of stopping immediately on the terminal container state; this is a diagnostic efficiency limitation, not 39 further application failures or a reason to retry.

The previous diagnostic had a running/healthy container but absent effective host publication. This run had an early container exit. Neither observed token validity or the exact task fixture. Do not attribute the change in container outcome to namespace entry without causal evidence. Do not use source-declared version 17.5.1 as an observed VERSION read; that step was never reached in either run.

## Contract and operational scope

Pinned upstream health documentation is archived in results/agentcompany-gitlab-health-contract-v1. It supports /-/health and the expected GitLab OK response for the application server; it explicitly does not make that response a database/dependency readiness proof. Successful later API reads would still be required. These docs do not prove packaged-source equivalence or change this run's outcome.

The public benchmark compose configuration includes restart: always, while these diagnostics deliberately used one fresh startup without automatic restart under their frozen stopping rules. That operational difference must be disclosed in any benchmark-feasibility claim. No broader claim that the original benchmark cannot run follows from these two diagnostics. Reproducing a benchmark restart policy would be a separate environment-adaptation decision, not a silent retry or a qualification pass here.

The two read-only diagnostic jobs total 1,767 seconds (29.45 minutes), each reporting zero billable execution milliseconds. That is a job-scoped audit, not a project or account invoice. No paid research models were called. Their two infrastructure failures remain separate from scientific denominators and from prior GitLab cohorts.

## Publication and next decision

The v2 protocol prohibits another transport-discovery iteration or automatic rerun. Preserve that closure. The retained GitLab task remains unqualified, with original instructions and setup semantics intact. A later deployment-policy adaptation would need a substantive feasibility/contribution assessment, explicit restart bounds, consistent conditions for every comparator and a new registration; it cannot be justified as searching for a passing result. No such run is dispatched by this closeout.

One ephemeral internal service secret printed in the failing reconfiguration log was redacted from the published copy. publication-redactions.json records original and published hashes and the single replaced field; the original is retained outside the repository. The failure message and all scientific/infrastructure decision evidence are unchanged. This is the only publication redaction in this archive.

Reconstruct using scripts/extension/verify_agentcompany_gitlab_fixture_v2.py --verify. Published archive: results/agentcompany-gitlab-fixture-ci-44060852176. Outcome: manifests/agentcompany-gitlab-fixture-outcome-v2.json. The research goal remains open: one ownCloud ordinary task is qualified, while the independent-input study and Q1 contribution are not established.
