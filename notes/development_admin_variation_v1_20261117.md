# Nine-case native workflow experiment: no incompatible accepted state

Frozen at 818e315 before execution; run 44106848687 completed all nine cases once in fresh separate jobs. The unchanged control and all six firstName/lastName/email omission/null variants returned 201, persisted, loaded in the native editor, and saved the unrelated edit with 200 and matching readback. Login omission and null returned 400 and had no continuation. There were no disabled-save observations, repairs, page errors, or observed non-target changes. These are correlated variants of one exposed workflow, not nine independent units.

Email omission and null persisted as null, appeared empty in the original native control, and remained null in both the successful update body and final readback. A screenshot of the email-null editor was visually inspected and shows the blank email field with enabled Save. This is a valid counterexample to inferring a required constraint from an error-message branch or nonNullable control option.

## Protocol correction

The frozen protocol incorrectly said that original source shows native email is required. The HTML contains an errors.required message branch, but the already exposed TypeScript initializer lists minLength(5), maxLength(254), and email validators, with no Validators.required for email. The runner did not impose or assert an email-required rule; it observed native save behavior. The inaccurate sentence is retained in the frozen protocol and corrected here rather than silently rewritten. The observed null-email behavior is consistent with the active form declarations. No further variants or reruns are added to recover a positive finding.

## Cost and contribution

GitHub reports nine Ubuntu jobs, run duration 346000 ms and total billable_ms 0. The retained timing metadata is a service report, not a monetary invoice. No paid API/model calls were used. Application/browser timings are retained per case and must not be interpreted as a controlled performance comparison.

All nine ZIP digests matched their GitHub artifact metadata before extraction. The summarizer checks the complete schedule, source revision, isolated interfaces, request statuses, bounded writes, object identity, unrelated edit, ordinary control, and non-target state differences. No natural incompatibility or causal repair effect was demonstrated. Independent evaluation cases added: zero. Q1 readiness and the independent study remain incomplete.

The next work is to settle and freeze the independent comparison design and workflow-selection rules, including schema and equivalent API-continuation baselines. Do not expand this exposed workflow's perturbations based on the negative outcome. The reserved frame remains unopened at implementation level. The related-work check also rules out claiming that bypass testing or UI-derived API tests are themselves new.
