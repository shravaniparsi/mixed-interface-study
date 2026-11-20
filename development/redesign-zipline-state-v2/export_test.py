import importlib.util,json,pathlib,tempfile
spec=importlib.util.spec_from_file_location('public_export',pathlib.Path(__file__).with_name('export.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
secret='fixture-test-token-123'
v=m.clean({'body':json.dumps({'token':secret,'id':'record-1'}),'CORE_SECRET':'anything-secret','password':False,'destination':'https://example.com'},[secret])
assert secret not in json.dumps(v) and json.loads(v['body'])['id']=='record-1' and v['password'] is False and v['CORE_SECRET']=='[REDACTED]'
with tempfile.TemporaryDirectory() as t:
 p=pathlib.Path(t);(p/'evidence').mkdir();(p/'redaction-values.json').write_text(json.dumps([secret]));(p/'evidence/result.json').write_text(json.dumps({'status':'failed','error':secret}));(p/'evidence/failure.html').write_text(secret)
 r=m.export(p);assert r['omitted']==['failure.html'];assert secret not in (p/'public-evidence/result.json').read_text();assert not (p/'public-evidence/failure.html').exists()
print('export tests passed: nested credentials, preserved scientific fields, omitted HTML, exact-value scan')
