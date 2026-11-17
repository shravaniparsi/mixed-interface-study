# Browser interaction contract: design requirements

This source diagnosis follows the closed ordinary run 44052230460. It does not reopen that run or register a new dispatch. The last turn was progress: a complete bounded control was archived, including the failed comparisons. This design step resolves what evidence a defensible future harness would need.

## Supported mechanism and remaining uncertainty

Pinned upstream core 097d4d22e0cf3341c4923e26453efb32ddedfb24, file-upload.js, reads #free_space during its add callback. A nonnegative value smaller than the selected byte count sets the observed error and returns before upload. files.js requests getstoragestats.php asynchronously and writes response.data.freeSpace into that field. filelist.js starts this statistics update after a directory response and renders a viewport-sized first page. list.php permits the initial field to be empty when freeSpace is unspecified. JavaScript numerically coerces an empty string to zero in the upload comparison. These source paths offer a plausible explanation for a premature file selection; they do not establish that the archived runtime followed that sequence.

The screenshot's zero-space message and later HTML's positive value are separate observations at different times. No timestamped value at selection, initial response body, callback trace or packaged byte comparison for these newly read files was collected. The onboarding dialog and 14-row list are independently visible in the saved evidence. A dialog may interfere with navigation, but its presence alone does not explain the missing upload request.

## Required interaction contract before another qualification

1. Attach passive request/response and UI-state logging before login. Capture directory PROPFIND and storage-statistics response bodies, timestamps, target directory and status. Do not issue additional application reads to make an asynchronous result appear sooner. Redact authentication headers; use only isolated public benchmark fixtures.
2. Dismiss the visible first-login dialog through its normal close control and record the action. Do not disable the application or mutate onboarding state through an API. Bound the wait and fail explicitly if the expected dialog state cannot be established.
3. Await successful completion and application of the target directory's initial statistics response before selecting a file. Require a defined, parseable value and record it immediately before selection. Do not require sufficient space as a readiness condition: a real low-space value must remain eligible to produce a failure. A negative sentinel also needs its source-defined meaning preserved. No fixed sleep can stand in for readiness evidence.
4. Navigate the actual file-list scroll container with bounded UI scrolling until the named row is rendered or the directory's end is reached. Record rows after each action. Do not inject a row, call private _nextPage directly, or use an API-generated share as a fallback. A missing rendered row after bounded navigation remains a failure, even if API readback succeeds.
5. Match observations across paths. If new readiness data enters a scientific oracle, provide the same information and a comparably timed observation budget to the API baseline. Browser initialization is distinct from additional producer readbacks; both must be accounted for. Do not change earlier scores using these new observations.
6. Preserve identical payload bytes, requested destination, public read-only share semantics, fresh fixtures and unauthenticated final download. Retain all failed readiness and navigation outcomes. A new engineering version must state its fixed limits before execution and distinguish itself from scientific effectiveness testing.

## Contribution gate

A reliable harness is necessary but not a publishable method by itself. It cannot establish natural-defect prevalence, incremental detection, or selector superiority. Before a scientific extension, the independent-input and competent-baseline design must distinguish deliberate invalid-input mutations from externally authored task instances, disclose all source/outcome exposure and preserve the full selection denominator. Do not turn this exposed initialization hypothesis into a held-out discovery claim.

Machine reconstruction: scripts/extension/audit_agentcompany_owncloud_readiness_v1.py --verify. Newly archived upstream files retain their license and are not claimed byte-equivalent to the packaged application. No applications ran for this diagnostic.
