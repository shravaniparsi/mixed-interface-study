// Source-mapped serializer for the registered non-LLM crawl fixture only.
// Runtime wire parity with the native editor is mandatory before experiments.
export function normalizeEditorUrl(raw) {
  const trimmed = raw.trim();
  if (!trimmed || /^https?:\/\//i.test(trimmed) || /^[a-z][a-z0-9+.-]*:/i.test(trimmed)
      || /^[a-z][a-z0-9+.-]*\/\/\//i.test(trimmed)) return trimmed;
  return `https://${trimmed}`;
}

export function crawlEditBody(readback, field, value) {
  if (!['name', 'url'].includes(field) || typeof value !== 'string') throw new Error('Unsupported edit');
  const robot = structuredClone(readback);
  const meta = robot.recording_meta;
  const workflow = robot.recording?.workflow;
  if (meta?.type !== 'crawl' || meta.isLLM === true || !Array.isArray(workflow)) {
    throw new Error('Outside registered crawl fixture');
  }
  // These fields are fixed in every registered producer, never varied.
  if (JSON.stringify(meta.formats) !== '["markdown"]') throw new Error('Unqualified output formats');
  let crawlConfig;
  for (const pair of workflow) {
    if (!Array.isArray(pair.what)) throw new Error('Incomplete workflow readback');
    for (const action of pair.what) {
      if (!['flag', 'crawl', 'goto', 'waitForLoadState'].includes(action.action)) {
        throw new Error('Unqualified action; cannot assume empty credentials/limits');
      }
      if (action.action === 'crawl' && action.args?.[0] && typeof action.args[0] === 'object') {
        crawlConfig = action.args[0]; // Original editor retains the last crawl configuration.
      }
    }
  }
  if (!crawlConfig) throw new Error('Missing crawl configuration');
  meta[field] = value;
  const lastPair = workflow[workflow.length - 1];
  const target = meta.url || lastPair?.what.find(action => action.action === 'goto')?.args?.[0] || '';
  const updatedWorkflow = workflow.map(pair => ({...pair, what: pair.what.map(action =>
    action.action === 'crawl' ? {...action, args: [{...crawlConfig}]} : action)}));
  // Match JSON serialization, including omission of undefined name and retention of null.
  return JSON.parse(JSON.stringify({
    name: meta.name, limits: [], credentials: {}, targetUrl: normalizeEditorUrl(target),
    workflow: updatedWorkflow, formats: [...meta.formats],
  }));
}

// Exact JSON-value equality: object order irrelevant; identities, timestamps,
// array order and all properties retained. No projection/normalization occurs.
export function sameState(left, right) {
  if (left === right) return true;
  if (left === null || right === null || typeof left !== 'object' || typeof right !== 'object') return false;
  if (Array.isArray(left) !== Array.isArray(right)) return false;
  const keys = Object.keys(left), other = Object.keys(right);
  if (keys.length !== other.length) return false;
  return keys.every(key => Object.hasOwn(right, key) && sameState(left[key], right[key]));
}
