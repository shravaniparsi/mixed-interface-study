/** Cross-check retained private actor evidence. Performs no request or DB query. */
import assert from 'node:assert/strict';
import { createHash, createPublicKey, verify } from 'node:crypto';
const sha = value => createHash('sha256').update(typeof value === 'string' ? value : JSON.stringify(value)).digest('hex');
const uuid = value => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
const single = (events, kind, id) => {
  const rows = events.filter(x => x.kind === kind && x.id === id);
  assert.equal(rows.length, 1, 'Missing or duplicate actor network evidence');
  return rows[0];
};
export function verifySeatsurfingActor({ accessToken, refreshToken, publicKey, events, database, organizationId,
  origin = 'http://127.0.0.1:8080', nowMs = Date.now(), expectedContinuity = null }) {
  assert.equal(origin, 'http://127.0.0.1:8080');
  assert.ok(Number.isSafeInteger(nowMs));
  assert.ok(uuid(organizationId) && uuid(refreshToken));
  assert.ok(typeof accessToken === 'string' && accessToken.length < 16384);
  const parts = accessToken.split('.'); assert.equal(parts.length, 3);
  for (const part of parts) assert.match(part, /^[A-Za-z0-9_-]+$/);
  const header = JSON.parse(Buffer.from(parts[0], 'base64url'));
  assert.equal(header.alg, 'RS512'); assert.equal(header.typ, 'JWT');
  const key = createPublicKey(publicKey); assert.equal(key.asymmetricKeyType, 'rsa');
  assert.equal(verify('RSA-SHA512', Buffer.from(parts[0] + '.' + parts[1]), key, Buffer.from(parts[2], 'base64url')), true, 'Invalid original token signature');
  const claims = JSON.parse(Buffer.from(parts[1], 'base64url'));
  assert.ok(uuid(claims.userID) && uuid(claims.sid) && uuid(claims.jti));
  assert.ok(typeof claims.iss === 'string' && claims.iss.length > 0);
  assert.deepEqual(claims.aud, [claims.iss]);
  for (const field of ['iat', 'nbf', 'exp']) assert.ok(Number.isSafeInteger(claims[field]));
  assert.ok(claims.iat * 1000 <= nowMs && claims.nbf * 1000 <= nowMs);
  assert.ok(claims.exp * 1000 > nowMs + 120000, 'Insufficient unchanged token lifetime');
  assert.ok(Array.isArray(events) && events.length <= 5000);
  const requests = events.filter(e => e.kind === 'request' && e.method === 'GET' && e.url === origin + '/user/me');
  assert.ok(requests.length > 0, 'Native self response not observed');
  let nativeSelf;
  for (const request of requests) {
    const headers = single(events, 'request_headers', request.id).headers;
    assert.equal(headers.authorization, 'Bearer ' + accessToken);
    const response = single(events, 'response', request.id);
    assert.equal(response.status, 200); assert.equal(response.bodyCaptured, true);
    assert.equal(response.bodySha256, sha(response.body));
    single(events, 'finished', request.id);
    assert.equal(events.some(e => e.kind === 'request_failed' && e.id === request.id), false);
    const value = JSON.parse(response.body);
    assert.equal(value.id, claims.userID); assert.equal(value.email, claims.email);
    assert.equal(value.organizationId, organizationId); assert.equal(value.organization.id, organizationId);
    assert.equal(value.accountType, 0); assert.equal(value.requirePassword, true);
    assert.equal(value.passwordPending, false);
    assert.ok(Array.isArray(value.roleIds) && value.roleIds.length > 0 && value.roleIds.every(uuid));
    assert.equal(new Set(value.roleIds).size, value.roleIds.length);
    assert.ok(value.permissions && typeof value.permissions === 'object' && !Array.isArray(value.permissions));
    assert.ok(Object.keys(value.permissions).length > 0 && Object.values(value.permissions).every(v => Number.isInteger(v) && v >= 0));
    const continuity = { userId: value.id, email: value.email, organizationId: value.organizationId,
      accountType: value.accountType, roleIds: [...value.roleIds].sort(), permissions: value.permissions,
      requirePassword: value.requirePassword, passwordPending: value.passwordPending,
      totpEnabled: value.totpEnabled, hasPasskeys: value.hasPasskeys, authProviderId: value.authProviderId,
      sessionId: claims.sid, issuer: claims.iss, accessTokenSha256: sha(accessToken), refreshTokenSha256: sha(refreshToken) };
    if (nativeSelf) assert.deepEqual(continuity, nativeSelf, 'Native actor changed within trace');
    nativeSelf = continuity;
  }
  const { user, session, refreshToken: refresh, assignments, roles } = database;
  assert.ok(user && session && refresh);
  assert.equal(user.id, claims.userID); assert.equal(user.email, claims.email);
  assert.equal(user.organization_id, organizationId); assert.equal(user.account_type, 0);
  assert.equal(user.disabled, false); assert.equal(database.banInactive, true);
  assert.equal(session.id, claims.sid); assert.equal(session.user_id, user.id);
  assert.equal(refresh.id, refreshToken); assert.equal(refresh.user_id, user.id);
  assert.equal(refresh.session_id, session.id); assert.equal(refresh.used_at, null);
  assert.ok(Number.isFinite(database.observedAtMs) && Math.abs(database.observedAtMs - nowMs) < 30000, 'Stale actor DB evidence');
  assert.ok(Number.isFinite(database.sessionExpiresAtMs) && Number.isFinite(database.refreshExpiresAtMs));
  assert.ok(database.sessionExpiresAtMs > nowMs + 120000 && database.refreshExpiresAtMs > nowMs + 120000);
  assert.ok(Array.isArray(assignments) && assignments.length > 0 && Array.isArray(roles));
  for (const assignment of assignments) {
    assert.equal(assignment.user_id, user.id);
    assert.equal(assignment.scope_type, ''); assert.equal(assignment.scope_id, '');
  }
  const roleIds = [...new Set(assignments.map(a => a.role_id))].sort();
  assert.deepEqual(roleIds, nativeSelf.roleIds);
  assert.deepEqual(roles.map(r => r.id).sort(), roleIds);
  assert.ok(roles.every(r => r.organization_id === organizationId));
  assert.ok(roles.some(r => r.system === true), 'Original administrator system role missing');
  if (expectedContinuity !== null) assert.deepEqual(nativeSelf, expectedContinuity, 'Actor differs across branches');
  return { identityConsistent: true, continuity: nativeSelf, databaseEvidenceSha256: sha(database),
    networkEvidenceSha256: sha(events), publicKeySha256: sha(publicKey),
    databaseAcquisitionProvenanceVerified: false, fullStateEqualityEstablished: false, runtimeQualified: false };
}
