# changedetection.io tag/group mapping

Wave 48 acquired and verified all eight scheduled original source files at freeze 470070e635806eb63fb25af383ddafa83bb9f7bd. Exposure totals 29 slots and 472258 decoded bytes. No application or scientific cases executed.

The native tag/group create and edit routes consume request.form. Creation validates and strips the name and rejects duplicate titles. Editing loads the existing tag into group_restock_settings_form, bridges processor_config dictionaries into nested FormFields, checks tag_colour, updates form.data, assigns processor=restock_diff, commits and clears associated watch checksums. The editor contains multiple text settings. Its inherited restock form and full conversions remain unmapped.

The original authenticated, OpenAPI-decorated JSON API calls create_tag/update_tag. These strip internal/read-only properties as applicable, reject unknown fields, check colour and persist. API creation may reuse an existing title, unlike native creation. Update checks notification URLs and clears watch checksums. Shared persistence calls do not establish complete request or state equivalence. Original schema/decorator and authentication requirements remain essential.

Tag inherits watch_base and EntityPersistenceMixin; TagsDict removes tag.json and its directory on deletion. This source design is not an executed persistence or restore qualification.

Incidental exposure includes commented-out whole-form validation, selective colour validation, the API-to-form configuration bridge and a template-translation issue reference. No issue was fetched and no mutation inputs or defect claims were selected from these comments.

Retain the watch and tag candidates. Neither currently supplies the complete native JSON request required by the registered comparison. Tag is not declared ineligible or runtime-qualified; whole-project coverage is unresolved. Mapping more inherited fields alone would not resolve the form-versus-JSON matching requirement.
