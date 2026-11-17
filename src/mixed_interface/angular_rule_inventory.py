"""Conservative inventory of flat Angular signal-form declarations.

Not a TypeScript parser, semantic validator or API mapping inference engine.
Unrecognized structure rejects the entire schema rather than discarding guards.
"""
import hashlib
import re


def inventory(source, source_id):
    digest = hashlib.sha256(source.encode()).hexdigest()
    result = dict(source_id=source_id, source_sha256=digest, status='unsupported_schema_structure', candidates=[], unsupported=[])
    matches = list(re.finditer(r'export const (\w+) = schema<(\w+)>\(path => \{\n([\s\S]*?)\n\}\);',source))
    if len(matches) != 1:
        return result
    match = matches[0]
    # Reject a schema-looking declaration inside a block comment. This conservative
    # lexical guard is not a substitute for a general TypeScript parser.
    if any(c.start() <= match.start() < c.end() for c in re.finditer(r'/\*[\s\S]*?\*/',source)):
        return result
    # Require a single explicit forms/signals import with unaliased identifiers.
    imports = re.findall(r"import \{([^}]+)\} from ['\"]@angular/forms/signals['\"];",source)
    if len(imports) != 1:
        return result
    names = [x.strip() for x in imports[0].split(',')]
    if any(not re.fullmatch(r'\w+',name) for name in names):
        return result
    statements=[]
    start_line=source[:match.start(3)].count('\n')+1
    for offset,line in enumerate(match[3].splitlines()):
        if not line.strip():
            continue
        call=re.fullmatch(r'\s*(\w+)\(path\.(\w+)(?:, (.*))?\);\s*',line)
        if not call:
            result['unsupported']=[dict(line=start_line+offset,reason='non_flat_or_unrecognized_statement')]
            return result
        statements.append((start_line+offset,call))
    result['status']='flat_schema_inventoried'
    result['schema']=match[1];result['model']=match[2]
    for line,call in statements:
        name,field,args=call.groups()
        item=dict(field=field,validator=name,line=line,source_id=source_id,argument_text=args,
                  api_mapping='unresolved',semantic_lowering='not_performed')
        if name in names and name=='required' and args is None:
            item['declaration']='explicit_required_call';result['candidates'].append(item)
        elif name in names and name in {'minLength','maxLength'} and args and re.fullmatch(r'\d+',args):
            item['declaration']='explicit_literal_length_call';item['bound']=int(args);result['candidates'].append(item)
        else:
            item['reason']='unsupported_validator_or_nonliteral_argument';result['unsupported'].append(item)
    return result
