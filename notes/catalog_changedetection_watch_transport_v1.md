# changedetection.io watch transport and exposure review

Wave 43 acquired all four scheduled dependencies once at freeze
402799cdc1f31547205b24dfbd1b3cf2fbd4710e. No watch, network fetch, notification,
application qualification or scientific input was executed.

The retained edit template declares a POST form to ui.ui_edit.edit_page with a
CSRF token. Its Python handler constructs the original WTForms class from
request.form on POST. The separately retained API Watch resource exposes PUT
through update_watch with request.json. Their existence does not establish a
complete matched continuation between these distinct routes and parsers.

The acquired watch-settings script constructs an AJAX request for filter/text
preview, handles notification defaults and configures the preview UI. That
preview request is not the ordinary Save request. Global-settings handles field
unlocking, display controls, processor classes and timezone defaults. Neither
script defines a JSON Save serializer. plugins.js provides shared browser/AJAX
utilities; the inherited layout adds other scripts, including csrf.js. Those
remaining dependencies are not represented as exhaustively inspected, and no
JSON transport equivalence has been invented from the visible field names.

Two explicit source exposures must accompany any future interpretation. The
already acquired API Watch.py (wave 3, file 16, validate_time_schedule_limit)
describes an earlier form/API timezone validation gap and its correction. The
new global-settings script describes preventing password-manager autofill from
replacing a stored LLM API key. The watch-settings preview also comments on
avoiding unchecked-radio overwrites. These comments were encountered during
original dependency mapping. No issue, test, patch or old revision was fetched;
none is a new executed defect or a reason to choose producer inputs.

The watch candidate remains unqualified for the frozen complete native-JSON
matching requirement. This is not a claim that the JSON API cannot create or
update watches, nor an exhaustive project exclusion. Resolving the CSRF submit
hook and original API operations is the next bounded mapping step; a different
wire contract cannot silently replace the preregistered comparator.
