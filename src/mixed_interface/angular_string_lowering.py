"""Translate inventoried declarations into string-domain predicate templates.

Qualified only against inspected @angular/forms/signals 22.2.3 sources.
Templates are not API rules: mapping, active-field and workflow scope remain open.
"""
import hashlib
import re


def lower(source, inventory, angular_version):
    if angular_version != '22.2.3':
        raise ValueError('Framework version has not been qualified')
    if hashlib.sha256(source.encode()).hexdigest() != inventory['source_sha256']:
        raise ValueError('Inventory/source mismatch')
    result=dict(templates=[],unresolved=[],complete_api_rules=0)
    if inventory['status'] != 'flat_schema_inventoried':
        result['unresolved'].append(dict(reason='unsupported_schema_structure'))
        return result
    model=inventory['model']
    blocks=re.findall(r'export interface '+re.escape(model)+r' \{\n([^}]+)\n\}',source)
    if len(blocks)!=1:
        result['unresolved'].append(dict(reason='model_declaration_unresolved'));return result
    types={}
    for line in blocks[0].splitlines():
        match=re.fullmatch(r'\s*(\w+): (.+);',line)
        if not match or match[1] in types:
            result['unresolved'].append(dict(reason='unsupported_model_structure'));return result
        types[match[1]]=match[2]
    result['unresolved'].extend(dict(x,reason='validator_semantics_unsupported') for x in inventory['unsupported'])
    for item in inventory['candidates']:
        if types.get(item['field'])!='string':
            result['unresolved'].append(dict(item,reason='non_string_or_union_domain'));continue
        name=item['validator']
        if name=='required':
            predicate=dict(kind='present_nonnull');policy=dict(missing='reject',null='reject',empty='reject')
        else:
            predicate=dict(kind='length',minimum=item['bound'] if name=='minLength' else None,
                           maximum=item['bound'] if name=='maxLength' else None,units='utf16_code_units')
            policy=dict(missing='allow',null='allow',empty='allow')
        result['templates'].append(dict(field=item['field'],validator=name,line=item['line'],
            source_id=item['source_id'],domain='string_or_nullish_only',predicate=predicate,value_policy=policy,
            api_mapping='unresolved',field_activity='unresolved',workflow_scope='unresolved',framework_version=angular_version))
    return result
