import test from 'node:test';
import assert from 'node:assert/strict';
import { encodeSqliteValue } from './nginx_sqlite_checkpoint_v1.mjs';

test('keeps SQLite storage classes distinct, including empty values', () => {
  const values = [null, 1n, 1, '1', Buffer.from('1'), '', Buffer.alloc(0)];
  assert.equal(new Set(values.map((v) => JSON.stringify(encodeSqliteValue(v)))).size, values.length);
});
test('preserves integers beyond JavaScript safe precision and binary bytes', () => {
  assert.deepEqual(encodeSqliteValue(9223372036854775807n), ['integer', '9223372036854775807']);
  assert.deepEqual(encodeSqliteValue(Buffer.from([0, 255])), ['blob', 'AP8=']);
});
test('rejects unexpected objects rather than silently stringifying them', () => {
  assert.throws(() => encodeSqliteValue({}), TypeError);
  assert.throws(() => encodeSqliteValue(undefined), TypeError);
});
