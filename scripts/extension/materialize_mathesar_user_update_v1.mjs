/** Source-derived ordinary recipe. Native request qualification is still required. */
export function materializeMathesarUserUpdate(user, supportedLanguages, edit) {
  if (!user || typeof user !== 'object' || Array.isArray(user)) {
    throw new Error('Unsupported readback shape');
  }
  const required = ['id', 'username', 'email', 'full_name', 'display_language', 'is_superuser'];
  if (required.some((key) => !Object.hasOwn(user, key))) {
    throw new Error('Incomplete user readback');
  }
  if (!Number.isSafeInteger(user.id) || user.id <= 0 || typeof user.is_superuser !== 'boolean') {
    throw new Error('Unsupported user identity/admin representation');
  }
  const stringFields = ['username', 'email', 'full_name', 'display_language'];
  if (stringFields.some((key) => user[key] !== null && typeof user[key] !== 'string')) {
    throw new Error('Unsupported non-string persisted field');
  }
  if (!Array.isArray(supportedLanguages) || !supportedLanguages.includes('en') ||
      supportedLanguages.some((item) => typeof item !== 'string')) {
    throw new Error('Unsupported page-language context');
  }
  const language = user.display_language ?? 'en';
  // Other Select auto-selection branches are deliberately not approximated.
  if (!supportedLanguages.includes(language)) {
    throw new Error('Unsupported persisted language outside page options');
  }
  if (!edit || !stringFields.includes(edit.field) || typeof edit.value !== 'string') {
    throw new Error('Unsupported unrelated edit');
  }
  if (edit.field === 'display_language' && !supportedLanguages.includes(edit.value)) {
    throw new Error('Unsupported language edit');
  }
  const baseUser = {
    full_name: user.full_name ?? '',
    username: user.username ?? '',
    email: user.email ?? '',
    display_language: language,
  };
  baseUser[edit.field] = edit.value;
  return {
    jsonrpc: '2.0',
    id: 0,
    method: 'users.patch_other',
    params: {
      ...baseUser,
      user_id: user.id,
      is_superuser: user.is_superuser,
    },
  };
}
