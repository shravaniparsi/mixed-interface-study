'use strict';
// Syntax inventory only: no runtime equivalence, complete validation, or API rules.
const crypto=require('crypto');
function inventory(ts,source){
 const file=ts.createSourceFile('component.ts',source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TS);
 const result={status:'inventoried',source_sha256:crypto.createHash('sha256').update(source).digest('hex'),forms:[],unresolved:[],observed_calls:[],observed_conditions:[],complete_api_rules:0};
 const txt=n=>n?.getText(file),at=n=>file.getLineAndCharacterOfPosition(n.getStart(file)).line+1;
 const walk=(n,fn)=>{fn(n);ts.forEachChild(n,c=>walk(c,fn));};
 const unknown=(n,reason)=>({status:'unsupported',expression:txt(n),line:at(n),reason});
 if(file.parseDiagnostics.length){result.status='parse_error';return result;}
 const imported=new Set();
 for(const n of file.statements)if(ts.isImportDeclaration(n)&&n.moduleSpecifier.text==='@angular/forms'&&!n.importClause?.isTypeOnly&&n.importClause?.namedBindings&&ts.isNamedImports(n.importClause.namedBindings))for(const e of n.importClause.namedBindings.elements)if(!e.propertyName&&!e.isTypeOnly)imported.add(e.name.text);
 const classes=file.statements.filter(ts.isClassDeclaration);
 if(classes.length!==1){result.status='unresolved';result.unresolved.push({reason:'class_not_unique'});return result;}
 const klass=classes[0],builders=new Set();
 for(const member of klass.members)if(ts.isConstructorDeclaration(member))for(const p of member.parameters)if(imported.has('FormBuilder')&&txt(p.type)==='FormBuilder'&&ts.isIdentifier(p.name)&&p.modifiers?.some(m=>[ts.SyntaxKind.PrivateKeyword,ts.SyntaxKind.PublicKeyword,ts.SyntaxKind.ProtectedKeyword,ts.SyntaxKind.ReadonlyKeyword].includes(m.kind)))builders.add(p.name.text);
 function validators(n){
  if(!n)return [];
  if(ts.isArrayLiteralExpression(n))return n.elements.flatMap(validators);
  if(ts.isCallExpression(n)&&txt(n.expression)==='Validators.compose'&&imported.has('Validators')&&n.arguments.length===1&&ts.isArrayLiteralExpression(n.arguments[0]))return validators(n.arguments[0]);
  const expression=ts.isCallExpression(n)?n.expression:n;
  if(!imported.has('Validators')||!ts.isPropertyAccessExpression(expression)||txt(expression.expression)!=='Validators')return [unknown(n,'validator_not_supported_builtin')];
  const name=expression.name.text,args=ts.isCallExpression(n)?n.arguments:[];
  if(['required','requiredTrue','email'].includes(name)&&!ts.isCallExpression(n))return [{status:'recognized_declaration',validator:name,line:at(n)}];
  if(['minLength','maxLength','min','max'].includes(name)&&args.length===1&&ts.isNumericLiteral(args[0]))return [{status:'recognized_declaration',validator:name,argument:Number(args[0].text),line:at(n)}];
  if(name==='pattern'&&args.length===1&&(ts.isStringLiteral(args[0])||args[0].kind===ts.SyntaxKind.RegularExpressionLiteral))return [{status:'recognized_declaration',validator:name,argument_source:txt(args[0]),argument_kind:ts.isStringLiteral(args[0])?'string':'regexp',line:at(n)}];
  return [unknown(n,'builtin_arguments_or_kind_unsupported')];
 }
 function control(n,builder){
  let initial,options,async;
  if(builder&&ts.isArrayLiteralExpression(n)){[initial,options,async]=n.elements;if(n.elements.length>3)return {status:'unsupported_control',reason:'excess_builder_arguments',expression:txt(n),line:at(n)};}
  else if(ts.isNewExpression(n)&&txt(n.expression)==='FormControl'&&imported.has('FormControl')){
   if((n.arguments?.length||0)>3)return {status:'unsupported_control',reason:'excess_constructor_arguments',expression:txt(n),line:at(n)};
   [initial,options,async]=n.arguments||[];
  }else return {status:'unsupported_control',reason:'control_structure_unresolved',expression:txt(n),line:at(n)};
  const out={status:'control_declaration',line:at(n),initial_expression:txt(initial)??null,validators:[],options:[],unresolved:[]};
  if(options&&ts.isObjectLiteralExpression(options)){
   const seen=new Set();
   for(const p of options.properties){
    if(!ts.isPropertyAssignment(p)||!ts.isIdentifier(p.name)||seen.has(p.name.text)){out.unresolved.push(unknown(p,'options_spread_computed_or_duplicate'));continue;}
    seen.add(p.name.text);
    if(p.name.text==='validators')out.validators.push(...validators(p.initializer));
    else if(['nonNullable','updateOn','initialValueIsDefault'].includes(p.name.text))out.options.push({name:p.name.text,expression:txt(p.initializer),runtime_semantics:'unqualified'});
    else out.unresolved.push(unknown(p,'option_or_async_behavior_unqualified'));
   }
  }else out.validators=validators(options);
  if(async)out.unresolved.push(unknown(async,'async_validator_unqualified'));
  return out;
 }
 walk(klass,n=>{
  if(ts.isIfStatement(n)||ts.isConditionalExpression(n))result.observed_conditions.push({expression:txt(ts.isIfStatement(n)?n.expression:n.condition),line:at(n),scope:'condition_observed_not_classified_as_validator'});
  if(ts.isCallExpression(n)&&ts.isPropertyAccessExpression(n.expression)&&['reset','setValue','patchValue','disable','enable','setValidators','addValidators','removeValidators','clearValidators','setAsyncValidators','getRawValue'].includes(n.expression.name.text))result.observed_calls.push({method:n.expression.name.text,expression:txt(n),line:at(n),scope:'call_observed_not_resolved_dataflow'});
  const group=ts.isNewExpression(n)&&txt(n.expression)==='FormGroup'&&imported.has('FormGroup');
  const builder=ts.isCallExpression(n)&&ts.isPropertyAccessExpression(n.expression)&&n.expression.name.text==='group'&&ts.isPropertyAccessExpression(n.expression.expression)&&n.expression.expression.expression.kind===ts.SyntaxKind.ThisKeyword&&builders.has(n.expression.expression.name.text);
  if(!group&&!builder)return;
  const form={kind:group?'FormGroup':'FormBuilder.group',line:at(n),binding:null,context:'unresolved',controls:[],unresolved:[]};result.forms.push(form);
  if(ts.isPropertyDeclaration(n.parent)&&n.parent.initializer===n){form.binding=txt(n.parent.name);form.context='class_property_initializer';}
  else if(ts.isBinaryExpression(n.parent)&&n.parent.right===n&&n.parent.operatorToken.kind===ts.SyntaxKind.EqualsToken){form.binding=txt(n.parent.left);form.context='assignment_execution_context_unqualified';}
  const args=n.arguments||[];
  if(!args.length||!ts.isObjectLiteralExpression(args[0])){form.unresolved.push(unknown(n,'group_object_unresolved'));return;}
  const seen=new Set();
  for(const p of args[0].properties){
   if(!ts.isPropertyAssignment(p)||(!ts.isIdentifier(p.name)&&!ts.isStringLiteral(p.name))){form.unresolved.push(unknown(p,'group_spread_or_computed_field'));continue;}
   const field=p.name.text;if(seen.has(field)){form.unresolved.push(unknown(p,'duplicate_field'));continue;}seen.add(field);
   form.controls.push({field,...control(p.initializer,builder)});
  }
  for(const extra of args.slice(1))form.unresolved.push(unknown(extra,'group_options_or_validators_unqualified'));
 });
 result.unqualified=['framework_runtime_version','import_resolution_and_shadowing','execution_guards_and_submission_logic','control_mutation_effects','template_directives','disabled_value_vs_raw_value','source_to_api_mapping','independent_contract_validity'];
 return result;
}
module.exports={inventory};
