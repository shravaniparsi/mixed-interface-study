"""Literal template declarations only; HTMLParser is not Angular's compiler.

No directive resolution, browser execution, activity inference or API rule output.
"""
from html.parser import HTMLParser
import hashlib
import re

VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
CONSTRAINTS={'required','minlength','maxlength','min','max','pattern','email'}
BINDINGS={'[(ngmodel)]','[ngmodel]','formcontrolname','[formcontrolname]','[formcontrol]'}

def inventory(source, source_id):
    result=dict(status='syntactic_inventory',source_id=source_id,source_sha256=hashlib.sha256(source.encode()).hexdigest(),forms=[],controls=[],submission_elements=[],unresolved=[],complete_api_rules=0)
    if re.search(r'@(if|for|switch|defer)\s*[({]',source):
        result['unresolved'].append(dict(reason='angular_block_control_flow_not_parsed'))
    class Parser(HTMLParser):
        def __init__(self):super().__init__(convert_charrefs=True);self.stack=[]
        def handle_starttag(self,tag,attrs):
            line=self.getpos()[0];mapping={};duplicates=[]
            for name,value in attrs:
                if name in mapping:duplicates.append(name)
                mapping[name]=value
            contexts=[dict(tag=n['tag'],line=n['line'],attributes=n['context']) for n in self.stack if n['context']]
            own_context={k:v for k,v in attrs if k.startswith('*') or k in {'[hidden]','hidden','[ngif]','[ngforof]'}}
            if own_context:contexts.append(dict(tag=tag,line=line,attributes=own_context))
            forms=[n['form_index'] for n in self.stack if n['form_index'] is not None]
            form_index=None
            if tag=='form':
                form_index=len(result['forms']);result['forms'].append(dict(line=line,attributes=[dict(name=k,value=v) for k,v in attrs],context=contexts))
                if forms:result['unresolved'].append(dict(line=line,reason='nested_form_browser_structure_unqualified'))
            is_control=tag in {'input','select','textarea'} or any(k in BINDINGS for k,v in attrs)
            if is_control:
                row=dict(tag=tag,line=line,form_indices=forms,bindings=[dict(name=k,value=v) for k,v in attrs if k in BINDINGS],input_type=mapping.get('type'),name=mapping.get('name'),context=contexts,constraints=[],dynamic_constraints=[],activity_attributes=[],other_attributes=[],unresolved=[])
                if duplicates:row['unresolved'].append(dict(reason='duplicate_attributes',names=duplicates))
                for key,value in attrs:
                    if key in CONSTRAINTS:
                        candidate=dict(attribute=key,value=value,status='literal_declaration')
                        if value is not None and ('{{' in value or '}}' in value):candidate.update(status='unresolved',reason='interpolated_constraint')
                        elif key in {'required','email'} and value not in (None,''):candidate.update(status='unresolved',reason='boolean_attribute_coercion_unqualified')
                        elif key in {'minlength','maxlength'} and (value is None or not re.fullmatch(r'\d+',value)):candidate.update(status='unresolved',reason='nonliteral_length')
                        elif key in {'min','max'}:candidate.update(status='unresolved',reason='input_domain_and_numeric_date_semantics_unqualified')
                        row['constraints'].append(candidate)
                    elif key.startswith('[') and key.endswith(']') and key[1:-1].removeprefix('attr.') in CONSTRAINTS:
                        row['dynamic_constraints'].append(dict(attribute=key,expression=value,status='unresolved'))
                    elif key in {'disabled','readonly','[disabled]','[readonly]','[attr.disabled]','[attr.readonly]'}:
                        row['activity_attributes'].append(dict(attribute=key,expression=value,status='unresolved_activity'))
                    elif key not in BINDINGS:row['other_attributes'].append(dict(name=key,value=value))
                if 'form' in mapping:row['unresolved'].append(dict(reason='explicit_form_owner_unqualified'))
                if tag not in {'input','select','textarea'}:row['unresolved'].append(dict(reason='custom_control_directives_unqualified'))
                result['controls'].append(row)
            if tag=='button' or tag=='form' or (tag=='input' and mapping.get('type') in {'submit','image'}):
                result['submission_elements'].append(dict(tag=tag,line=line,attributes=[dict(name=k,value=v) for k,v in attrs],context=contexts,semantics='unqualified'))
            if tag not in VOID:self.stack.append(dict(tag=tag,line=line,context=own_context,form_index=form_index))
        def handle_startendtag(self,tag,attrs):
            self.handle_starttag(tag,attrs)
            if tag not in VOID:self.handle_endtag(tag)
        def handle_endtag(self,tag):
            indices=[i for i,n in enumerate(self.stack) if n['tag']==tag]
            if not indices:
                result['unresolved'].append(dict(line=self.getpos()[0],reason='unmatched_closing_tag',tag=tag));return
            index=indices[-1]
            if index!=len(self.stack)-1:result['unresolved'].append(dict(line=self.getpos()[0],reason='implicit_closing_structure_unqualified',tag=tag))
            del self.stack[index:]
    parser=Parser()
    try:
        parser.feed(source);parser.close()
        if parser.stack:result['unresolved'].append(dict(reason='unclosed_tags',tags=[n['tag'] for n in parser.stack]))
    except Exception as error:result.update(status='parse_error',error_type=type(error).__name__,message=str(error))
    result['unqualified']=['angular_compiler_parse','directive_resolution','framework_version_semantics','browser_constraint_validation','runtime_field_activity','submission_guards','model_and_api_mapping','independent_contract_validity']
    return result
