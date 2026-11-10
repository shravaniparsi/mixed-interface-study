"""Identify recorded form measurements affected by the frozen name-selector defect."""
from pathlib import Path
import hashlib,json

OLD_ADAPTER_SHA256='3efc3c794f774428285908d226c814af421360d79dfa9b7e67c6aec0ff22ce0e'

def measurement_issue(attempt_directory):
    root=Path(attempt_directory)/'runtime/run'
    adapter=root/'executed-adapter.mjs'
    if not adapter.is_file() or hashlib.sha256(adapter.read_bytes()).hexdigest()!=OLD_ADAPTER_SHA256:
        return None
    affected=[]
    for path in sorted(root.glob('*/result.json')):
        value=json.loads(path.read_text())
        stored=value.get('stored_prefix',{}).get('jobDataMap',{})
        if not stored:continue
        for form in value.get('ui_forms',[]):
            if form.get('typed_entries')==[]:
                affected.append({'raw_result':str(path.relative_to(Path(attempt_directory))),
                    'raw_result_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                    'form_label':form['label'],'bound_map':stored,'recorded_entries':[],
                    'native_preview':form.get('preview_text')})
    if not affected:return None
    return {'kind':'quartz_dynamic_name_selector_measurement_invalid',
            'adapter_sha256':OLD_ADAPTER_SHA256,'affected_form_measurements':affected,
            'interpretation':'The frozen reader omitted rendered map rows. These channel comparisons cannot establish application defects; original observations remain unchanged.'}
