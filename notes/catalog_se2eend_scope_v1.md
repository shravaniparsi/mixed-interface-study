# sE2EEnd: outside the registered create-and-edit scope

Wave 40 acquired the six published blobs once at source revision
2903709f0833de69f0a53575f47fd449a3b9d265. Together with waves 1–3, the retained
source now covers all six Java classes in the declared controller directory,
the native route configuration, profile, upload/dashboard pages, admin settings
and the download page. No application or scientific case was executed.

SendController creates and reads Send records and deletes them; it exposes no
scalar metadata update. AdminController lists, deletes and revokes Sends and
performs cleanup. SendDownloadController downloads or destroys a Send.
FileController uploads multipart data; ChunkedUploadController initializes,
streams and completes file uploads. File uploads are outside the fixed scope
and do not establish a native scalar metadata editor.

The profile page displays identity and session values. AdminPage composes
statistics, settings and Send tables. SettingsPanel submits one PATCH per fixed
key; InstanceSettingsService.set can create a missing key/value row, so these
writes must not be described as update-only database operations. Nevertheless,
each record has only one editable value and a key fixed by its native control.
Combining different settings into an invented multi-property record would
change the registered comparison unit. DownloadPage offers password entry,
view/download and destruction, without a scalar metadata edit action.

The declared native routes and server controllers therefore do not support the
required record creation and editing pair with two independently editable
scalar text properties. This is a scope exclusion for the frozen application,
not a defect finding or a statement about modified deployments or external
Keycloak administration. The project remains in the denominator of twelve,
receives no replacement, and consumes no application qualification jobs.

The v2 scope-exclusion manifest retains all 21 acquired source identities and
the exact six-controller coverage. The SeatSurfing final attempt continues
independently; its outcome did not determine this source selection.
