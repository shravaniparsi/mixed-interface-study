'use strict';
// Certifies only the syntax of a direct return/body parameter, never network bytes.
const crypto=require('crypto');
function analyze(ts,source,methodNames){
 const file=ts.createSourceFile('service.ts',source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TS),out={source_sha256:crypto.createHash('sha256').update(source).digest('hex'),methods:[],complete_runtime_http_mappings:0};
 const text=n=>n?.getText(file),line=n=>file.getLineAndCharacterOfPosition(n.getStart(file)).line+1,walk=(n,f)=>{f(n);ts.forEachChild(n,c=>walk(c,f));};
 if(file.parseDiagnostics.length){out.status='parse_error';return out;}
 const classes=file.statements.filter(ts.isClassDeclaration);if(classes.length!==1){out.status='class_unresolved';return out;}const klass=classes[0];out.class_name=text(klass.name);
 const httpImported=file.statements.some(n=>ts.isImportDeclaration(n)&&n.moduleSpecifier.text==='@angular/common/http'&&!n.importClause?.isTypeOnly&&n.importClause?.namedBindings&&ts.isNamedImports(n.importClause.namedBindings)&&n.importClause.namedBindings.elements.some(e=>e.name.text==='HttpClient'&&!e.propertyName&&!e.isTypeOnly));
 const receivers=new Map();for(const m of klass.members)if(ts.isConstructorDeclaration(m))for(const p of m.parameters)if(ts.isIdentifier(p.name)&&p.modifiers?.some(x=>[ts.SyntaxKind.PrivateKeyword,ts.SyntaxKind.PublicKeyword,ts.SyntaxKind.ProtectedKeyword,ts.SyntaxKind.ReadonlyKeyword].includes(x.kind)))receivers.set(p.name.text,text(p.type));
 for(const name of methodNames){
  const methods=klass.members.filter(n=>ts.isMethodDeclaration(n)&&text(n.name)===name);const row={method:name,status:'unresolved',calls:[]};out.methods.push(row);
  if(methods.length!==1||!methods[0].body){row.reason='method_not_unique';continue;}const method=methods[0];row.line=line(method);row.parameters=method.parameters.map(p=>text(p.name));
  walk(method.body,n=>{if(!ts.isCallExpression(n)||!ts.isPropertyAccessExpression(n.expression)||!['post','put','patch'].includes(n.expression.name.text))return;const receiver=n.expression.expression;if(!ts.isPropertyAccessExpression(receiver)||receiver.expression.kind!==ts.SyntaxKind.ThisKeyword||!receivers.has(receiver.name.text))return;row.calls.push({line:line(n),receiver:text(receiver),receiver_type:receivers.get(receiver.name.text),verb:n.expression.name.text.toUpperCase(),url_expression:text(n.arguments[0]),body_expression:text(n.arguments[1]),node:n});});
  const statements=method.body.statements,call=row.calls[0];
  if(row.calls.length!==1)row.reason='write_call_not_unique';
  else if(!httpImported||call.receiver_type!=='HttpClient')row.reason='wrapper_not_httpclient';
  else if(statements.length!==1||!ts.isReturnStatement(statements[0])||statements[0].expression!==call.node)row.reason='not_single_direct_return';
  else {const body=call.node.arguments[1];const index=body&&ts.isIdentifier(body)?method.parameters.findIndex(p=>ts.isIdentifier(p.name)&&p.name.text===body.text):-1;if(index<0)row.reason='body_not_direct_parameter';else Object.assign(row,{status:'direct_httpclient_parameter_syntax',body_parameter_index:index,body_parameter:body.text});}
  for(const c of row.calls)delete c.node;
  row.local_initializers=[];walk(method.body,n=>{if(ts.isVariableDeclaration(n)&&n.initializer)row.local_initializers.push({name:text(n.name),expression:text(n.initializer),line:line(n)});});
 }
 out.unqualified=['configuration_endpoint_resolution','http_interceptors_and_serialization','runtime_dependency_injection','indirect_side_effects','independent_contract_validity'];return out;
}
module.exports={analyze};
