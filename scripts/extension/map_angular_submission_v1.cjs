'use strict';
// Static, bounded AST mapping. Does not load or execute application modules.
const fs = require('fs');
const crypto = require('crypto');
const assert = require('assert');
const hash = s => crypto.createHash('sha256').update(s).digest('hex');
function analyze(ts, componentText, serviceText, schemaName, fields) {
  const parse = (name,text) => {
    const file=ts.createSourceFile(name,text,ts.ScriptTarget.Latest,true,ts.ScriptKind.TS);
    assert.equal(file.parseDiagnostics.length,0,'Parse diagnostics prohibit mapping');return file;
  };
  const component=parse('component.ts',componentText), service=parse('service.ts',serviceText);
  const walk=(node,fn)=>{fn(node);ts.forEachChild(node,c=>walk(c,fn));};
  const text=n=>n && n.getText();
  const strip=n=>ts.isAsExpression(n)||ts.isParenthesizedExpression(n)?strip(n.expression):n;
  const property=(obj,name)=>ts.isObjectLiteralExpression(obj)?obj.properties.find(p=>ts.isPropertyAssignment(p)&&text(p.name)===name):undefined;
  const fail=reason=>({status:'unresolved',reason,mappings:[]});
  // Require directly imported form identifier; unsupported aliases are not guessed.
  const formImports=component.statements.filter(n=>ts.isImportDeclaration(n)&&n.moduleSpecifier.text==='@angular/forms/signals');
  if(!formImports.some(n=>n.importClause?.namedBindings && ts.isNamedImports(n.importClause.namedBindings)&&n.importClause.namedBindings.elements.some(e=>e.name.text==='form'&&!e.propertyName)))return fail('form_import_unqualified');
  const formCalls=[];
  walk(component,n=>{if(ts.isCallExpression(n)&&text(n.expression)==='form'&&text(n.arguments[1])===schemaName)formCalls.push(n);});
  if(formCalls.length!==1)return fail('form_binding_not_unique');
  const call=formCalls[0],model=text(call.arguments[0]);
  if(!/^this\.\w+$/.test(model))return fail('model_not_direct_property');
  const submission=property(call.arguments[2],'submission');
  const action=submission && property(submission.initializer,'action')?.initializer;
  if(!action || !ts.isArrowFunction(action))return fail('submission_callback_unresolved');
  const serviceClasses=service.statements.filter(ts.isClassDeclaration);
  if(serviceClasses.length!==1)return fail('service_class_not_unique');
  const klass=serviceClasses[0],serviceName=text(klass.name);
  const injected=[];
  walk(component,n=>{if(ts.isPropertyDeclaration(n)&&n.initializer&&ts.isCallExpression(n.initializer)&&text(n.initializer.expression)==='inject'&&text(n.initializer.arguments[0])===serviceName)injected.push(text(n.name));});
  if(injected.length!==1)return fail('service_injection_unresolved');
  const submits=[];
  walk(action.body,n=>{if(ts.isCallExpression(n)&&ts.isPropertyAccessExpression(n.expression)&&text(n.expression.expression)==='this.'+injected[0])submits.push(n);});
  if(submits.length!==1)return fail('submission_service_call_not_unique');
  const submit=submits[0],methodName=submit.expression.name.text;
  const methods=klass.members.filter(n=>ts.isMethodDeclaration(n)&&text(n.name)===methodName);
  if(methods.length!==1)return fail('service_method_unresolved');
  const method=methods[0],httpProperties=klass.members.filter(n=>ts.isPropertyDeclaration(n)&&n.initializer&&ts.isCallExpression(n.initializer)&&text(n.initializer.expression)==='inject'&&text(n.initializer.arguments[0])==='HttpClient');
  if(httpProperties.length!==1)return fail('http_injection_unresolved');
  const requests=[];
  walk(method.body,n=>{if(ts.isCallExpression(n)&&ts.isPropertyAccessExpression(n.expression)&&text(n.expression.expression)==='this.'+text(httpProperties[0].name)&&['post','put','patch'].includes(n.expression.name.text))requests.push(n);});
  if(requests.length!==1)return fail('http_write_not_unique');
  const request=requests[0],body=request.arguments[1];
  if(!body||!ts.isIdentifier(body))return fail('http_body_transformed');
  const index=method.parameters.findIndex(p=>text(p.name)===body.text);
  if(index<0||!submit.arguments[index])return fail('body_parameter_unresolved');
  // Reject assignments to any identifier/property in the service method: no hidden
  // local mutation analysis is claimed. Calls/interceptors remain separately unqualified.
  let assignment=false;
  walk(method.body,n=>{if(ts.isBinaryExpression(n)&&n.operatorToken.kind>=ts.SyntaxKind.FirstAssignment&&n.operatorToken.kind<=ts.SyntaxKind.LastAssignment)assignment=true;});
  walk(action.body,n=>{if(ts.isBinaryExpression(n)&&n.operatorToken.kind>=ts.SyntaxKind.FirstAssignment&&n.operatorToken.kind<=ts.SyntaxKind.LastAssignment)assignment=true;});
  if(assignment)return fail('assignment_requires_dataflow');
  let payload=strip(submit.arguments[index]);
  if(ts.isIdentifier(payload)) {
    const aliases=[];
    walk(action.body,n=>{if(ts.isVariableDeclaration(n)&&text(n.name)===payload.text)aliases.push(n);});
    if(aliases.length!==1 || !(aliases[0].parent.flags & ts.NodeFlags.Const) || !aliases[0].initializer)return fail('payload_alias_unresolved');
    payload=strip(aliases[0].initializer);
  }
  if(!ts.isObjectLiteralExpression(payload))return fail('payload_not_literal');
  const spreads=payload.properties.filter(ts.isSpreadAssignment);
  if(spreads.length!==1||payload.properties[payload.properties.length-1]!==spreads[0])return fail('spread_overrides_unresolved');
  const spread=strip(spreads[0].expression);
  if(!ts.isCallExpression(spread)||text(spread.expression)!==model||spread.arguments.length!==0)return fail('spread_not_bound_model');
  for(const p of payload.properties.filter(p=>p!==spreads[0])) {
    if(!ts.isPropertyAssignment(p)||fields.includes(text(p.name)))return fail('payload_property_overlap');
  }
  return {status:'source_boundary_mapping',schema:schemaName,model,service_method:methodName,
    http_method:request.expression.name.text.toUpperCase(),url_expression:text(request.arguments[0]),
    mappings:fields.map(field=>({field,request_path:[field],relation:'identity_if_present_in_form_model'})),
    source_hashes:{component:hash(componentText),service:hash(serviceText)},
    unqualified:['field_activity','actor_and_lifecycle','model_initialization_and_defaults','http_interceptors','indirect_call_side_effects','import_resolution_and_shadowing','runtime_serialization','persisted_state','independent_contract_validity']};
}
module.exports={analyze};
if(require.main===module){
 const [parser,component,service,schema,fields]=process.argv.slice(2);
 const ts=require(parser);assert.equal(ts.version,'6.0.3');
 console.log(JSON.stringify(analyze(ts,fs.readFileSync(component,'utf8'),fs.readFileSync(service,'utf8'),schema,fields.split(',')),null,2));
}
