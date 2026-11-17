# Infrastructure correction for paired ordinary controls

Version 1 is closed at run 44105021413: the API arm qualified; the UI arm did not execute because H2 startup raised UnknownHostException for the runner hostname inside the loopback-only network namespace. This is a setup failure, not a UI workflow failure.

Version 2 repeats both fixed arms once, in fresh separate jobs, with unchanged business inputs, browser runner, application JAR, dependencies, limits and outcome checks from v1. The only runtime correction appends the validated runner hostname to loopback in the ephemeral runner hosts file and verifies local resolution before startup, retaining that observation. External networking remains unavailable to application/browser. No application code or validation is changed. The v1 outcomes remain archived; v2 does not add independent cases. A further failure is retained, without automatic retry.
