import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.shared_reconstruction import digest,package_shared_evidence
S=ROOT/'manifests/development-confirmation-schedule-v1.json'
source=json.loads(S.read_text());rows=[]
for case in source['rows']:
    obs=dict(target='submit_decision',point='candidate_api_projection',
             context=dict(revision='29f5a77069bee0163e3cfebbb6fd5969f23160a1',operation='register',actor='authored_development_actor',lifecycle='direct_original_method_after_fresh_reset'),
             document={**{k:case['form'][k] for k in ['login','email','password']},'langKey':case['language']})
    for supplied in [False,True]:
        facts=[]
        if supplied:
            for key,value in [('form.snapshot',case['form']),('translation.language',case['language'])]:
                facts.append(dict(id=key,status='known',value=value,origin='provided_context',evidence=str(S.relative_to(ROOT))+'#'+case['id'],observation_sha256=digest(obs)))
        package=package_shared_evidence(obs,['form.snapshot','translation.language'],facts)
        expected='unknown' if not supplied else ('would_emit' if case['expected']['save_calls'] else 'would_not_emit')
        rows.append(dict(id=case['id']+(':complete' if supplied else ':request-only'),shared=package,expected=expected))
value=dict(kind='exposed_shared_comparison_schedule',source_schedule_sha256=hashlib.sha256(S.read_bytes()).hexdigest(),rows=rows)
out=ROOT/'manifests/development-shared-comparison-schedule-v1.json';text=json.dumps(value,indent=2)+'\n'
if '--verify' in sys.argv:assert out.read_text()==text
else:out.write_text(text)
