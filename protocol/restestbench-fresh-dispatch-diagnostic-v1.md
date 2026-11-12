# One fresh dispatch to distinguish old-handle failure

After user authorization to diagnose and proceed, minimal runner run 43132605142 succeeded, and full unit run 43132778538 succeeded at f534545. The unchanged old qualification handle 43096414710 again ended in startup_failure with zero jobs. Its page still shows an internal-error annotation (request ID EDA6:1940C9:9D7235:A78AED:6AF51257), not a workflow syntax error. No qualification test has run.

Use one fresh workflow_dispatch on a dedicated branch pointing exactly to b137f849a95b28adf0013c3d0a36458dbb819920. This keeps the workflow, application runner, dependencies, service scope, tests and concurrency group identical, while creating a new run handle. The diagnostic contrast is old-handle rerun versus fresh dispatch under demonstrated current runner availability. Do not attribute historical causation solely from this contrast.

This new submission is authorized within the user's request to complete diagnosis and proceed. It is registered before dispatch. All started application jobs, including any from this new handle, remain bounded by the existing three initial jobs/75 minutes and four total jobs/100 minutes. Preserve every earlier zero-job failure. No new scientific case, changed assertion, paid model call or larger runner is introduced.

If the new handle also fails before scheduling, isolate workflow features with non-application diagnostics; do not repeatedly submit qualification or change scientific inputs. If it starts, proceed with the existing valid-service protocol and archive the full result with the new run ID explicitly recorded.
