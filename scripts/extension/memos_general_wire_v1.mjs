/** Strict observation decoder for pinned Memos GENERAL updates, not a protobuf SDK.
 * Source: b40d8a7b573774c52b022c8d6537d6baf2129dc0 proto/api/user_service.proto.
 * Unknown/duplicate singular fields fail qualification instead of disappearing.
 * Raw bytes must be retained separately. Proto3 scalar defaults are explicit below.
 */
const utf8 = new TextDecoder('utf-8', {fatal: true});
function fields(bytes) {
  const result = []; let pos = 0;
  function uint() {
    let value = 0n;
    for (let i = 0; i < 10; i++) {
      if (pos >= bytes.length) throw Error('Truncated varint');
      const b = bytes[pos++];
      if (i === 9 && b > 1) throw Error('Varint overflow');
      value |= BigInt(b & 127) << BigInt(i * 7);
      if (!(b & 128)) return value;
    }
    throw Error('Unterminated varint');
  }
  while (pos < bytes.length) {
    const tag = uint(); const id = Number(tag >> 3n); const wire = Number(tag & 7n);
    if (id < 1 || id > 536870911) throw Error('Invalid field number');
    let value;
    if (wire === 0) value = uint();
    else if (wire === 2) {
      const length = uint();
      if (length > BigInt(bytes.length - pos)) throw Error('Truncated field');
      value = bytes.subarray(pos, pos + Number(length)); pos += Number(length);
    } else throw Error('Unsupported wire type');
    result.push({id, wire, value});
  }
  return result;
}
function decode(bytes, schema, defaults = {}) {
  const result = {...defaults}; const seen = new Set();
  for (const {id, wire, value} of fields(bytes)) {
    const spec = schema[id];
    if (!spec) throw Error('Unexpected field ' + id);
    const [name, type, repeated = false] = spec;
    if (!repeated && seen.has(id)) throw Error('Duplicate singular field ' + id);
    seen.add(id);
    if (wire !== (type === 'bool' ? 0 : 2)) throw Error('Wrong wire type');
    let item;
    if (type === 'bool') {
      if (value !== 0n && value !== 1n) throw Error('Noncanonical boolean');
      item = value === 1n;
    } else item = type === 'string' ? utf8.decode(value) : type(value);
    if (repeated) (result[name] ??= []).push(item); else result[name] = item;
  }
  return result;
}
const general = b => decode(b, {
  1: ['locale','string'], 2: ['memoVisibility','string'],
  3: ['theme','string'], 4: ['saveMediaMetadata','bool'],
}, {locale:'', memoVisibility:'', theme:'', saveMediaMetadata:false});
const setting = b => decode(b, {1:['name','string'], 2:['generalSetting',general]}, {name:''});
const mask = b => decode(b, {1:['paths','string',true]}, {paths:[]});
export function decodeGeneralUpdate(bytes, contentType) {
  if (contentType.split(';')[0].trim().toLowerCase() !== 'application/proto')
    throw Error('Unqualified content type');
  if (!(bytes instanceof Uint8Array)) throw Error('Raw bytes required');
  const result = decode(bytes, {1:['userSetting',setting], 2:['updateMask',mask]});
  if (!result.userSetting?.generalSetting || !result.updateMask?.paths.length)
    throw Error('Missing setting or mask');
  if (!/^users\/[^/]+\/settings\/GENERAL$/.test(result.userSetting.name))
    throw Error('Not an owned GENERAL resource name');
  const allowed = new Set(['locale','memo_visibility','theme','save_media_metadata']);
  if (result.updateMask.paths.some(p => !allowed.has(p))) throw Error('Unexpected mask');
  return result;
}
