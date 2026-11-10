/** Strict observation decoder for pinned Memos memo audience-only updates, not a protobuf SDK.
 * Source: b40d8a7b573774c52b022c8d6537d6baf2129dc0 proto/api/memo_service.proto.
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
    if (wire !== (['bool','uint'].includes(type) ? 0 : 2)) throw Error('Wrong wire type');
    let item;
    if (type === 'bool') {
      if (value !== 0n && value !== 1n) throw Error('Noncanonical boolean');
      item = value === 1n;
    } else if(type === 'uint'){
      if(value > BigInt(Number.MAX_SAFE_INTEGER)) throw Error('Unsafe integer');
      item=Number(value);
    } else item = type === 'string' ? utf8.decode(value) : type(value);
    if (repeated) (result[name] ??= []).push(item); else result[name] = item;
  }
  return result;
}
const memo = b => decode(b, {1:['name','string'],4:['content','string'],6:['visibility','uint']}, {name:'',content:'',visibility:0});
const mask = b => decode(b, {1:['paths','string',true]}, {paths:[]});
export function decodeMemoAudienceUpdate(bytes, contentType) {
  if(contentType.split(';')[0].trim().toLowerCase() !== 'application/proto') throw Error('Unqualified content type');
  if(!(bytes instanceof Uint8Array)) throw Error('Raw bytes required');
  const result=decode(bytes,{1:['memo',memo],2:['updateMask',mask]});
  if(!result.memo || !/^memos\/[^/]+$/.test(result.memo.name)) throw Error('Memo resource required');
  if(!result.updateMask || result.updateMask.paths.length!==1 || result.updateMask.paths[0]!=='visibility') throw Error('Not an audience-only edit');
  if(![1,2,3,4].includes(result.memo.visibility)) throw Error('Unqualified audience enum');
  return result;
}
