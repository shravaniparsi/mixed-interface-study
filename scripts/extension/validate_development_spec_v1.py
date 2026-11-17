#!/usr/bin/env python3
"""Validate fixed API-only input and preserve full selected-operation reference closure."""
import argparse,hashlib,importlib.metadata,json,platform
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'results/development-spec-startup-v2-ci-44089249914/openapi.body'
OUT=ROOT/'manifests/development-spec-validation-v1.json'
SELECTED=[('/api/register','post'),('/api/admin/users','post'),('/api/admin/users','put')]
def refs(value):
    if isinstance(value,dict):
        if '$ref' in value:yield value['$ref']
        for v in value.values():yield from refs(v)
    elif isinstance(value,list):
        for v in value:yield from refs(v)
def pointer(doc,ref):
    if not isinstance(ref,str) or not ref.startswith('#/'):raise ValueError('nonlocal_reference')
    value=doc
    for key in ref[2:].split('/'):
        key=key.replace('~1','/').replace('~0','~')
        value=value[int(key)] if isinstance(value,list) else value[key]
    return value
def build():
    raw=SOURCE.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    assert sha=='2c8546ccc3d04eb7166aec4a10aea1434a89a25ea3f78188bd3df5d0b8231af1'
    doc=json.loads(raw)
    result=dict(kind='development_api_only_input_validation',source_sha256=sha,python=platform.python_version(),
        versions={},validation='not_run',selected_operations=[],independent_evaluation_cases=0,baseline_qualified=False)
    try:
        for ref in refs(doc):pointer(doc,ref)
        for key in ['openapi-spec-validator','openapi-schema-validator','jsonschema']:
            result['versions'][key]=importlib.metadata.version(key)
        assert result['versions']=={'openapi-spec-validator':'0.7.2','openapi-schema-validator':'0.6.3','jsonschema':'4.26.0'}
        from openapi_spec_validator import validate_spec
        validate_spec(doc)
        result['validation']='valid'
    except Exception as error:result.update(validation='failed',error_type=type(error).__name__,message=str(error))
    for path,method in SELECTED:
        operation=doc.get('paths',{}).get(path,{}).get(method)
        row=dict(path=path,method=method,status='absent' if operation is None else 'present',operation=operation,references={})
        if operation is not None:
            queue=list(refs(operation))
            while queue:
                ref=queue.pop()
                if ref in row['references']:continue
                try:
                    value=pointer(doc,ref);row['references'][ref]=value;queue.extend(refs(value))
                except (ValueError,KeyError,IndexError,TypeError) as error:
                    row['references'][str(ref)]={'resolution_error':type(error).__name__}
        result['selected_operations'].append(row)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args()
    value=build();text=json.dumps(value,indent=2)+'\n'
    if a.verify:assert OUT.read_text()==text
    else:OUT.write_text(text)
    print(json.dumps({'validation':value['validation'],'operations':[(r['path'],r['method'],r['status'],len(r['references'])) for r in value['selected_operations']]}))
    raise SystemExit(0 if value['validation']=='valid' else 1)
