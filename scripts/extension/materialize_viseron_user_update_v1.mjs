/** Original UserDialog -> authUpdateUser request mapping; not native-qualified. */
export function materializeViseronUserUpdate(user, edit) {
  const required = ['id', 'name', 'username', 'role', 'enabled', 'assigned_cameras', 'preferences'];
  if (!user || typeof user !== 'object' || Array.isArray(user)
    || required.some((key) => !Object.hasOwn(user, key))) {
    throw new Error('Incomplete original user readback');
  }
  if (typeof user.id !== 'string' || !/^[0-9a-f]{32}$/.test(user.id)
    || typeof user.name !== 'string' || typeof user.username !== 'string'
    || !['admin', 'read', 'write'].includes(user.role) || typeof user.enabled !== 'boolean') {
    throw new Error('Unsupported persisted user representation');
  }
  if (user.assigned_cameras !== null && (!Array.isArray(user.assigned_cameras)
    || user.assigned_cameras.some((id) => typeof id !== 'string'))) {
    throw new Error('Unsupported camera-assignment representation');
  }
  if (user.preferences !== null && (typeof user.preferences !== 'object' || Array.isArray(user.preferences))) {
    throw new Error('Unsupported preferences readback');
  }
  if (!edit || !['name', 'username'].includes(edit.field) || typeof edit.value !== 'string') {
    throw new Error('Unsupported unrelated text edit');
  }
  const text = { name: user.name, username: user.username, [edit.field]: edit.value };
  // UserDialog starts from user.assigned_cameras || []; authUpdateUser then
  // converts an empty selection to null. The original network serializer does
  // not include preferences, enabled or id in the JSON body.
  const cameras = user.assigned_cameras ?? [];
  return {
    method: 'PUT',
    api_relative_path: `/auth/user/${user.id}`,
    body: { name: text.name, username: text.username, role: user.role,
      assigned_cameras: cameras.length > 0 ? [...cameras] : null },
  };
}
