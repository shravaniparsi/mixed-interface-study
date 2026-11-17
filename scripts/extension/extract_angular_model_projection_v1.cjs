'use strict';
// A deliberately bounded recognizer for a two-statement linkedSignal projection.
// Does not establish what the upstream signal returns or execute application code.
const crypto=require('crypto');
function analyze(ts,source,schemaName,fields){
 const fail=reason=>({status:'unresolved',reason,projection:null});
 const file=ts.createSourceFile('component.ts',source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TS);
 if(file.parseDiagnostics.length)return fail('parse_diagnostics');
 if(!Array.isArray(fields)||!fields.length||new Set(fields).size!==fields.length)return fail('invalid_field_inventory');
 const text=n=>n?.getText(file);
 const imports=(module,name)=>file.statements.filter(n=>ts.isImportDeclaration(n)&&n.moduleSpecifier.text===module&&n.importClause?.namedBindings&&!n.importClause.isTypeOnly&&ts.isNamedImports(n.importClause.namedBindings)).flatMap(n=>n.importClause.namedBindings.elements).filter(e=>e.name.text===name&&!e.propertyName&&!e.isTypeOnly);
 if(imports('@angular/core','linkedSignal').length!==1||imports('@angular/forms/signals','form').length!==1)return fail('imports_unqualified');
 if(file.statements.some(n=>!ts.isImportDeclaration(n)&&!ts.isClassDeclaration(n)))return fail('unsupported_top_level_binding');
 const classes=file.statements.filter(ts.isClassDeclaration);
 if(classes.length!==1)return fail('class_not_unique');
 const klass=classes[0];
 const members=klass.members.filter(ts.isPropertyDeclaration);
 const bindings=members.filter(n=>n.initializer&&ts.isCallExpression(n.initializer)&&text(n.initializer.expression)==='form'&&text(n.initializer.arguments[1])===schemaName);
 if(bindings.length!==1)return fail('form_binding_not_unique');
 const model=bindings[0].initializer.arguments[0];
 if(!model||!ts.isPropertyAccessExpression(model)||model.expression.kind!==ts.SyntaxKind.ThisKeyword)return fail('model_not_direct_property');
 const definitions=members.filter(n=>text(n.name)===model.name.text);
 if(definitions.length!==1)return fail('model_definition_not_unique');
 const init=definitions[0].initializer;
 if(!init||!ts.isCallExpression(init)||text(init.expression)!=='linkedSignal'||init.arguments.length!==1)return fail('unsupported_initializer');
 const callback=init.arguments[0];
 if(!ts.isArrowFunction(callback)||callback.parameters.length||!ts.isBlock(callback.body)||callback.body.statements.length!==2)return fail('unsupported_projection_body');
 const [statement,returned]=callback.body.statements;
 if(!ts.isVariableStatement(statement)||!(statement.declarationList.flags & ts.NodeFlags.Const)||statement.declarationList.declarations.length!==1||!ts.isReturnStatement(returned)||!returned.expression||!ts.isObjectLiteralExpression(returned.expression))return fail('unsupported_statements');
 const declaration=statement.declarationList.declarations[0],input=declaration.initializer;
 if(!ts.isObjectBindingPattern(declaration.name)||!input||!ts.isCallExpression(input)||input.arguments.length||!ts.isPropertyAccessExpression(input.expression)||input.expression.expression.kind!==ts.SyntaxKind.ThisKeyword)return fail('unsupported_input_binding');
 const assignments=[];
 for(const binding of declaration.name.elements){
   if(binding.dotDotDotToken||binding.propertyName||!ts.isIdentifier(binding.name)||!binding.initializer||!ts.isStringLiteral(binding.initializer))return fail('unsupported_default_or_alias');
   assignments.push({field:binding.name.text,source_path:[binding.name.text],when_missing_or_undefined:binding.initializer.text,null_behavior:'preserve',present_behavior:'identity'});
 }
 const names=assignments.map(a=>a.field);
 if(new Set(names).size!==names.length||names.length!==fields.length||fields.some(f=>!names.includes(f)))return fail('field_inventory_mismatch');
 if(returned.expression.properties.length!==names.length||returned.expression.properties.some((p,i)=>!ts.isShorthandPropertyAssignment(p)||p.objectAssignmentInitializer||p.name.text!==names[i]))return fail('return_not_exact_projection');
 return {status:'source_model_projection',schema:schemaName,model:text(model),input_expression:text(input.expression)+'()',source_sha256:crypto.createHash('sha256').update(source).digest('hex'),projection:assignments,
   unqualified:['upstream_signal_to_api_response','resource_state_and_fallback','actor_and_lifecycle','dynamic_field_activity','application_runtime','independent_contract_validity']};
}
function project(extraction,input){
 if(extraction.status!=='source_model_projection')return {status:'unknown',reason:'projection_unresolved'};
 // JSON-object domain only: getters/proxies/prototypes are not modeled.
 if(input===null||Array.isArray(input)||typeof input!=='object'||Object.getPrototypeOf(input)!==Object.prototype)return {status:'unknown',reason:'input_not_plain_object'};
 const output={};
 for(const item of extraction.projection){
  const property=Object.getOwnPropertyDescriptor(input,item.field);
  if(property&&(!Object.hasOwn(property,'value')))return {status:'unknown',reason:'accessor_not_supported'};
  const value=property?.value;
  Object.defineProperty(output,item.field,{value:value===undefined?item.when_missing_or_undefined:value,enumerable:true,writable:true,configurable:true});
 }
 return {status:'projected',model:output,scope:'value_returned_by_recorded_input_expression_only'};
}
module.exports={analyze,project};
