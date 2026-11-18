/** Original settled form mapping, unchanged parent/type selections; not native-qualified. */
export const organizationUpdateKeys = ["id", "organizationName", "shortName", "isActive", "lastupdated", "commune", "village", "department", "formName", "formMethod", "cancelAction", "submitOnCancel", "cancelMethod", "mlsSentinelLabFlag", "parentOrgName", "state", "internetAddress", "selectedTypes", "organization", "cliaNum", "streetAddress", "city", "email"];
export function materializeOpenElisOrganizationUpdate(readback, edit) {
  if (!readback || typeof readback !== 'object' || Array.isArray(readback)
      || organizationUpdateKeys.some((key) => !Object.hasOwn(readback, key))) {
    throw new Error('Complete original form readback required');
  }
  if (typeof readback.id !== 'string' || !/^[1-9][0-9]*$/.test(readback.id)) {
    throw new Error('Persisted organization identifier required');
  }
  if (!Array.isArray(readback.selectedTypes) || readback.selectedTypes.some((id) => typeof id !== 'string')) {
    throw new Error('Unsupported original type selection');
  }
  const fields = ['organizationName', 'shortName', 'streetAddress', 'city', 'email', 'cliaNum', 'internetAddress'];
  if (!edit || !fields.includes(edit.field) || typeof edit.value !== 'string') {
    throw new Error('Unsupported unrelated text edit');
  }
  const state = Object.fromEntries(organizationUpdateKeys.map((key) => [key, readback[key]]));
  // Only the original URL edit handler trims its new value.
  state[edit.field] = edit.field === 'internetAddress' ? edit.value.trim() : edit.value;
  return { method: 'POST',
    api_relative_path: `/rest/Organization?ID=${readback.id}&startingRecNo=1`,
    body: JSON.parse(JSON.stringify(state)) };
}
