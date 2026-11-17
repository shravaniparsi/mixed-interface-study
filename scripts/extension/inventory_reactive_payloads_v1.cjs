'use strict';
// Component-to-service syntax only, not HTTP mapping or whole-program dataflow.
const crypto=require('crypto');const {inventory}=require('./inventory_reactive_forms_v1.cjs');
function analyze(ts,source){
 const file=ts.createSourceFile('component.ts',source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TS),base=inventory(ts,source);
 const out={status:'inventoried',source_sha256:crypto.createHash('sha256').update(source).digest('hex'),calls:[],complete_api_rules:0};
 if(file.parseDiagnostics.length||base.status!=='inventoried'){out.status='unresolved';return out;}
 const txt=n=>n?.getText(file),line=n=>file.getLineAndCharacterOfPosition(n.getStart(file)).line+1;
 const forms=new Set(base.forms.map(f=>f.binding?.replace(/^this\./,'')).filter(Boolean));
 const klass=file.statements.filter(ts.isClassDeclaration)[0],services=new Map();
 for(const member of klass.members)if(ts.isConstructorDeclaration(member))for(const p of member.parameters)if(ts.isIdentifier(p.name)&&/Service$/.test(txt(p.type)||'')&&p.modifiers?.some(m=>[ts.SyntaxKind.PrivateKeyword,ts.SyntaxKind.PublicKeyword,ts.SyntaxKind.ProtectedKeyword,ts.SyntaxKind.ReadonlyKeyword].includes(m.kind)))services.set(p.name.text,txt(p.type));
 const walk=(n,f)=>{f(n);ts.forEachChild(n,c=>walk(c,f));};
 const unknown=(n,reason)=>({kind:'unresolved',expression:txt(n),reason,line:line(n)});
 function accessor(n){
  const raw=ts.isCallExpression(n)&&n.arguments.length===0&&ts.isPropertyAccessExpression(n.expression)&&n.expression.name.text==='getRawValue';
  const value=ts.isPropertyAccessExpression(n)&&n.name.text==='value';
  const receiver=raw?n.expression.expression:value?n.expression:null;
  if(receiver&&ts.isPropertyAccessExpression(receiver)&&receiver.expression.kind===ts.SyntaxKind.ThisKeyword&&forms.has(receiver.name.text))return {kind:'form_snapshot',form:receiver.name.text,accessor:raw?'getRawValue':'value',read_line:line(n)};
  return null;
 }
 const names=n=>ts.isIdentifier(n)?[n.text]:(ts.isObjectBindingPattern(n)||ts.isArrayBindingPattern(n))?n.elements.flatMap(e=>e.name?names(e.name):[]):[];
 function binding(identifier,location){
  for(let node=location.parent;node&&node!==klass;node=node.parent){
   if(ts.isBlock(node)){
    const found=[];
    for(const statement of node.statements){
     if(!ts.isVariableStatement(statement))continue;
     for(const d of statement.declarationList.declarations)if(names(d.name).includes(identifier))found.push({d,isConst:!!(statement.declarationList.flags&ts.NodeFlags.Const)});
    }
    if(found.length){if(found.length!==1)return {error:'ambiguous_binding'};if(found[0].d.getStart(file)>=location.getStart(file))return {error:'binding_before_initialization'};return found[0];}
   }
   if(node.parameters?.some(p=>names(p.name).includes(identifier)))return {error:'parameter_shadow'};
   if(ts.isCatchClause(node)&&node.variableDeclaration&&names(node.variableDeclaration.name).includes(identifier))return {error:'catch_binding'};
   if((ts.isForStatement(node)||ts.isForOfStatement(node)||ts.isForInStatement(node))&&node.initializer&&ts.isVariableDeclarationList(node.initializer)&&node.initializer.declarations.some(d=>names(d.name).includes(identifier)))return {error:'loop_binding'};
  }
  return {error:'binding_not_resolved'};
 }
 function mutated(name,location){
  let method=location;while(method&&!ts.isMethodDeclaration(method))method=method.parent;if(!method)return true;
  let changed=false;
  walk(method.body,n=>{if(n.getStart(file)>=location.getStart(file))return;
   if(ts.isBinaryExpression(n)&&n.operatorToken.kind>=ts.SyntaxKind.FirstAssignment&&n.operatorToken.kind<=ts.SyntaxKind.LastAssignment){let root=n.left;while(ts.isPropertyAccessExpression(root)||ts.isElementAccessExpression(root))root=root.expression;if(ts.isIdentifier(root)&&root.text===name)changed=true;}
   if((ts.isPrefixUnaryExpression(n)||ts.isPostfixUnaryExpression(n))&&[ts.SyntaxKind.PlusPlusToken,ts.SyntaxKind.MinusMinusToken].includes(n.operator)){let root=n.operand;while(ts.isPropertyAccessExpression(root)||ts.isElementAccessExpression(root))root=root.expression;if(ts.isIdentifier(root)&&root.text===name)changed=true;}
  });return changed;
 }
 function resolve(n,location,seen=new Set()){
  const direct=accessor(n);if(direct)return direct;
  if(ts.isIdentifier(n)){
   if(seen.has(n.text))return unknown(n,'alias_cycle');const next=new Set(seen);next.add(n.text);
   const found=binding(n.text,location);if(found.error)return unknown(n,found.error);
   if(!found.isConst||!found.d.initializer)return unknown(n,'mutable_or_uninitialized_binding');
   if(mutated(n.text,location))return unknown(n,'observed_alias_mutation');
   const d=found.d;
   if(ts.isIdentifier(d.name))return resolve(d.initializer,d,next);
   if(!ts.isObjectBindingPattern(d.name))return unknown(n,'binding_shape_unsupported');
   const element=d.name.elements.find(e=>ts.isIdentifier(e.name)&&e.name.text===n.text);
   if(!element||element.dotDotDotToken||element.initializer)return unknown(n,'destructure_default_or_rest');
   const field=element.propertyName||element.name;
   if(!ts.isIdentifier(field)&&!ts.isStringLiteral(field))return unknown(n,'computed_destructure');
   const read=resolve(d.initializer,d,next);return read.kind==='form_snapshot'?{...read,kind:'form_field_read',field:field.text}:unknown(n,'destructure_input_unresolved');
  }
  if(ts.isObjectLiteralExpression(n)){
   const fields=[],seenNames=new Set();
   for(const p of n.properties){
    if((!ts.isPropertyAssignment(p)&&!ts.isShorthandPropertyAssignment(p))||(!ts.isIdentifier(p.name)&&!ts.isStringLiteral(p.name))||p.objectAssignmentInitializer)return unknown(n,'payload_spread_computed_or_default');
    const name=p.name.text;if(seenNames.has(name))return unknown(n,'duplicate_payload_field');seenNames.add(name);
    const expression=ts.isPropertyAssignment(p)?p.initializer:p.name;fields.push({payload_field:name,source:resolve(expression,location,new Set(seen))});
   }
   return {kind:'literal_payload',fields};
  }
  return unknown(n,'expression_not_form_read');
 }
 walk(klass,n=>{
  if(!ts.isCallExpression(n)||!n.arguments.length||!ts.isPropertyAccessExpression(n.expression))return;
  const receiver=n.expression.expression;if(!ts.isPropertyAccessExpression(receiver)||receiver.expression.kind!==ts.SyntaxKind.ThisKeyword||!services.has(receiver.name.text))return;
  const guards=[];let child=n;
  for(let parent=n.parent;parent&&parent!==klass;child=parent,parent=parent.parent)if(ts.isIfStatement(parent))guards.push({condition:txt(parent.expression),branch:child===parent.thenStatement?'then':child===parent.elseStatement?'else':'unresolved',line:line(parent),meaning:'lexical_condition_not_proven_precondition'});
  out.calls.push({line:line(n),service_property:receiver.name.text,service_type:services.get(receiver.name.text),method:n.expression.name.text,arguments:n.arguments.map(a=>resolve(a,n)),lexical_guards:guards});
 });
 out.unqualified=['service_to_http_and_serialization','import_resolution_and_shadowing','indirect_mutation_and_alias_effects','async_execution_context','form_state_and_read_timing','guard_satisfiability','actor_and_lifecycle','independent_contract_validity'];return out;
}
module.exports={analyze};
