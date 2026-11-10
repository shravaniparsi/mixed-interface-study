# Bounded prior-issue check for exploratory energy observation

Checked 10 November 2026, after the ordinary-control full-record observation and after registering the separate replication. This search cannot establish that a behavior has never been reported.

Read-only GitHub issue searches used repository `grocy/grocy`, limit 100: `calories`, `energy`, `numberpicker`, `calories null`, `energy empty`, `calories default`. The broad calories output was truncated in the tool view and is not claimed to have been exhaustively reviewed. The three narrower queries returned one, zero and zero results respectively. Web searches for energy/null and numberpicker/null did not establish an exact prior report.

Inspected primary sources:

- [Issue 1733](https://github.com/grocy/grocy/issues/1733), especially [the maintainer's API example](https://github.com/grocy/grocy/issues/1733#issuecomment-1005704843): the demonstrated API-created product's returned representation includes null calories. Another comment explains the historic database/PDO origin of numeric-string representations. This supports treating null energy as a real API representation, rather than automatically declaring it a malformed response. It does not state that an unrelated native edit must preserve null and does not report the measured null-to-one transition.
- [Issue 1083](https://github.com/grocy/grocy/issues/1083): a historical prerelease number-picker defect rejected zero in decimal userfields and the energy input; the maintainer linked a fix. This is related numeric-widget history, but the described trigger/outcome differs from the current unrelated-rename observation.
- [Issue 1975](https://github.com/grocy/grocy/issues/1975): quantity-unit changes and conversion of product amount properties. It does not describe the null-energy rename trigger.

Status: no exact matching prior report established by this bounded check; novelty remains unproven. No message, issue or disclosure was sent. The candidate source mechanism remains the pinned optional energy numberpicker receiving null and its `isset`-based fallback. Experimental replication, requirement interpretation and broader issue/commit history remain necessary before any new-defect assertion. Historical maintainer examples are supporting context, not a specification of all current behavior.
