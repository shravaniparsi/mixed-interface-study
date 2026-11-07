import test from 'node:test';
import assert from 'node:assert/strict';
import {audit, command, enforce, profileBundle, profileForm, articleIdentity, commentPath,
  projectSnapshot, snapshot, rejectionState} from '../scripts/realworld_integrity.mjs';

function reads() {
  return [
    {path: '/api/user', status: 200, data: {user: {username: 'pilotresearch', email: 'pilot@example.com', bio: null, image: null, token: 'volatile'}}},
    {path: '/api/articles?author=pilotresearch', status: 200, data: {articlesCount: 1,
      articles: [{slug: 'one', title: 'One', body: 'original', tagList: ['b', 'a'], updatedAt: 'fixed'}]}},
    {path: '/api/articles/one/comments', status: 200, data: {comments: [{id: 7, body: 'same', author: {username: 'pilotresearch'}}]}},
    {path: '/api/tags', status: 200, data: {tags: ['a', 'b']}},
  ];
}
const observed = r => ({readable: true, data: projectSnapshot(r)});

test('submitted commands are exact: omission, null, extra fields and wrong identities differ', () => {
  const expected = command('PUT', '/api/user', {user: {bio: 'x'}});
  for (const actual of [command('PUT', '/api/user', {user: {bio: 'x', image: null}}),
    command('PUT', '/api/users/other', expected.payload), command('POST', '/api/user', expected.payload)]) {
    const guard = audit('payload', 'continuation', 'ui', expected, actual);
    assert.equal(guard.passed, false); assert.throws(() => enforce(guard), {name: 'OperationNotComparable'});
  }
});

test('object key order is immaterial but list order and scalar types remain exact for payloads', () => {
  assert.equal(audit('x', 'prefix', 'api', {a: 1, b: 2}, {b: 2, a: 1}).passed, true);
  assert.equal(audit('x', 'prefix', 'api', {tags: ['a', 'b']}, {tags: ['b', 'a']}).passed, false);
  assert.equal(audit('x', 'prefix', 'api', {id: 1}, {id: '1'}).passed, false);
});

test('settings command preserves the bound principal and omits only null image', () => {
  const u = {username: 'owner', email: 'owner@example.com', bio: null, image: null, token: 'secret'};
  assert.deepEqual(profileBundle(u, 'edit'), {user: {username: 'owner', email: 'owner@example.com', bio: 'edit'}});
  assert.equal(profileBundle({...u, image: ''}, 'edit').user.image, '');
  assert.deepEqual(profileForm(u), {username: 'owner', email: 'owner@example.com', bio: '', image: '', new_credential_blank: true});
});

test('comment deletion uses the returned id without guessing or coercion', () => {
  assert.equal(commentPath('a b', 7), '/api/articles/a%20b/comments/7');
  for (const id of [undefined, null, '7', 0, -1, NaN, 1.5]) assert.throws(() => commentPath('one', id));
});

test('loaded article binding keeps identity and treats tags as a set without changing command payloads', () => {
  const a = {slug: 'one', title: 'T', body: 'B', description: 'D', tagList: ['b', 'a', 'a'], author: {username: 'owner'}};
  assert.deepEqual(articleIdentity(a).tagList, ['a', 'b']);
  assert.notDeepEqual(articleIdentity(a), articleIdentity({...a, slug: 'other'}));
  assert.deepEqual(a.tagList, ['b', 'a', 'a']);
});

test('unchanged resource count cannot hide a modified article, principal or timestamp', () => {
  const before = reads();
  for (const change of [r => {r[1].data.articles[0].body = 'changed';},
    r => {r[0].data.user.email = 'other@example.com';},
    r => {r[1].data.articles[0].updatedAt = 'new';}, r => {r[3].data.tags.push('orphan');}]) {
    const after = reads(); change(after);
    assert.equal(rejectionState(observed(before), observed(after)), 'changed');
  }
});

test('same comment count cannot hide a different returned id or author', () => {
  for (const change of [r => {r[2].data.comments[0].id = 8;},
    r => {r[2].data.comments[0].author.username = 'other';}]) {
    const after = reads(); change(after);
    assert.equal(rejectionState(observed(reads()), observed(after)), 'changed');
  }
});

test('snapshot omits auth token and normalizes tag order, retaining business values', () => {
  const after = reads(); after[0].data.user.token = 'new'; after[1].data.articles[0].tagList = ['a', 'b', 'b'];
  assert.equal(rejectionState(observed(reads()), observed(after)), 'unchanged');
});

test('missing, partial, duplicate and failed probes cannot become unchanged state', () => {
  for (const change of [r => r.pop(), r => {r[1].data.articlesCount = 2;},
    r => {r[2].status = 500;}, r => r.push(r[2]), r => r[2].data.comments.push(r[2].data.comments[0])]) {
    const r = reads(); change(r); assert.throws(() => projectSnapshot(r));
  }
  assert.equal(rejectionState(observed(reads()), {readable: false}), 'unreadable');
  assert.equal(rejectionState(observed(reads()), null), 'unobserved');
});

test('snapshot captures failed HTTP and thrown transport probes without inventing state', async () => {
  const good = await snapshot(async (_method, path) => ({...reads().find(r => r.path === path), response_sequence: 4}));
  assert.equal(good.readable, true); assert.equal(good.reads.length, 4);
  const failed = await snapshot(async () => {throw new Error('transport failure');});
  assert.equal(failed.readable, false); assert.equal(failed.reads.length, 0);
  assert.equal(rejectionState(good, failed), 'unreadable');
});
