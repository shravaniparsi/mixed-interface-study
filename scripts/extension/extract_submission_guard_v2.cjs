'use strict';
const crypto = require('node:crypto');

// Static acquisition only: a branch predicate is not an API correctness oracle.
function extractGuard(ts, source, selection) {
  const sha256 = crypto.createHash('sha256').update(source).digest('hex');
  const no = reason => ({status: 'unsupported', reason, source_sha256: sha256});
  const file = ts.createSourceFile('input.ts', source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  if (file.parseDiagnostics.length) return no('parse_error');
  const classes = file.statements.filter(ts.isClassDeclaration);
  if (classes.length !== 1 || classes[0].heritageClauses?.some(h => h.token === ts.SyntaxKind.ExtendsKeyword)) return no('class_scope');
  const cls = classes[0];
  const methods = cls.members.filter(n => ts.isMethodDeclaration(n) && n.name.getText(file) === selection.method);
  if (methods.length !== 1 || !methods[0].body || methods[0].parameters.length) return no('method_scope');
  const method = methods[0];
  if (method.modifiers?.some(n => n.kind === ts.SyntaxKind.AsyncKeyword || n.kind === ts.SyntaxKind.StaticKeyword) || method.asteriskToken) return no('method_execution_kind');
  const path = n => {
    if (n.kind === ts.SyntaxKind.ThisKeyword) return ['this'];
    if (ts.isPropertyAccessExpression(n) && !n.questionDotToken) {
      const p = path(n.expression); return p ? [...p, n.name.text] : null;
    }
    return null;
  };
  const isPath = (n, p) => JSON.stringify(path(n)) === JSON.stringify(p);
  const bool = n => n && [ts.SyntaxKind.TrueKeyword, ts.SyntaxKind.FalseKeyword].includes(n.kind);
  const flags = new Set(cls.members.filter(n => ts.isPropertyDeclaration(n) && ts.isIdentifier(n.name) && bool(n.initializer) && !n.modifiers?.length).map(n => n.name.text));
  const harmless = n => ts.isExpressionStatement(n) && ts.isBinaryExpression(n.expression) && n.expression.operatorToken.kind === ts.SyntaxKind.EqualsToken && bool(n.expression.right) && path(n.expression.left)?.length === 2 && flags.has(path(n.expression.left)[1]);
  const aliases = new Map();
  function bind(n) {
    if (!ts.isVariableStatement(n) || n.declarationList.flags !== ts.NodeFlags.Const || n.declarationList.declarations.length !== 1) return false;
    const d = n.declarationList.declarations[0], call = d.initializer;
    if (!ts.isObjectBindingPattern(d.name) || !call || !ts.isCallExpression(call) || call.arguments.length || call.questionDotToken || !isPath(call.expression, ['this', selection.form, 'getRawValue'])) return false;
    for (const e of d.name.elements) {
      if (e.dotDotDotToken || e.initializer || !ts.isIdentifier(e.name) || (e.propertyName && !ts.isIdentifier(e.propertyName)) || aliases.has(e.name.text)) return false;
      aliases.set(e.name.text, e.propertyName?.text || e.name.text);
    }
    return true;
  }
  const statements = [...method.body.statements];
  const branch = statements.pop();
  if (!branch || !ts.isIfStatement(branch) || !branch.elseStatement || !ts.isBlock(branch.thenStatement) || !ts.isBlock(branch.elseStatement)) return no('terminal_binary_branch_required');
  for (const s of statements) if (!harmless(s) && !bind(s)) return no('unsupported_prefix');
  const c = branch.expression;
  if (!ts.isBinaryExpression(c) || ![ts.SyntaxKind.EqualsEqualsEqualsToken, ts.SyntaxKind.ExclamationEqualsEqualsToken].includes(c.operatorToken.kind) || !ts.isIdentifier(c.left) || !ts.isIdentifier(c.right) || !aliases.has(c.left.text) || !aliases.has(c.right.text)) return no('unsupported_condition');
  const payloadValue = n => ts.isIdentifier(n) && aliases.has(n.text) || ts.isStringLiteral(n) || (path(n)?.length === 3);
  function sink(s) {
    if (!ts.isExpressionStatement(s) || !ts.isCallExpression(s.expression)) return false;
    const outer = s.expression;
    if (outer.questionDotToken || !ts.isPropertyAccessExpression(outer.expression) || outer.expression.name.text !== 'subscribe' || outer.expression.questionDotToken) return false;
    const call = outer.expression.expression;
    if (!ts.isCallExpression(call) || call.questionDotToken || !isPath(call.expression, ['this', selection.service, selection.sink]) || call.arguments.length !== 1 || !ts.isObjectLiteralExpression(call.arguments[0])) return false;
    return call.arguments[0].properties.every(p => ts.isShorthandPropertyAssignment(p) && !p.objectAssignmentInitializer && aliases.has(p.name.text) || ts.isPropertyAssignment(p) && ts.isIdentifier(p.name) && payloadValue(p.initializer));
  }
  function arm(block) {
    let count = 0;
    for (const s of block.statements) {
      if (count) return null;
      if (harmless(s)) continue;
      // Snapshot aliases in a branch are local; restore them for its sibling.
      if (bind(s)) continue;
      if (sink(s)) { count++; continue; }
      return null;
    }
    return count;
  }
  const before = new Map(aliases), yes = arm(branch.thenStatement);
  aliases.clear(); for (const [k,v] of before) aliases.set(k,v);
  const noArm = arm(branch.elseStatement);
  if (yes === null || noArm === null || yes + noArm !== 1) return no('unsupported_branch_body');
  return {
    status: 'extracted', source_sha256: sha256,
    selection: {...selection}, selection_automatic: false,
    predicate: {left: before.get(c.left.text), operator: c.operatorToken.getText(file), right: before.get(c.right.text), sink_when: yes === 1},
    source_span: {start: c.getStart(file), end: c.getEnd()},
    target: 'branch_selects_sink',
    assumptions: ['plain fresh instance fields', 'stable getRawValue snapshot', 'payload construction and service access do not throw'],
    establishes_api_obligation: false,
  };
}
function evaluateGuard(rule, snapshot) {
  if (rule.status !== 'extracted') return 'unknown';
  const p = rule.predicate;
  if (!snapshot || ![p.left,p.right].every(k => Object.hasOwn(snapshot,k) && typeof snapshot[k] === 'string')) return 'unknown';
  const condition = p.operator === '===' ? snapshot[p.left] === snapshot[p.right] : snapshot[p.left] !== snapshot[p.right];
  return condition === p.sink_when ? 'sink_branch' : 'non_sink_branch';
}
module.exports = {extractGuard, evaluateGuard};
