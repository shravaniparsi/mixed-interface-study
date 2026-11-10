#!/usr/bin/env python3
"""Verify an explicitly registered immutable phase archive without changing evidence."""
import argparse,json
from pathlib import Path
from primary_preflight_v1 import ROOT,read
from primary_collection_v1 import collect
from mixed_interface.repetition import require

def verify(manifest_path):
    m=read(manifest_path);root=(ROOT/m['archive_root']).resolve();require(root.is_relative_to((ROOT/'results').resolve()),'Archive outside results')
    value=collect(root,m['mode']);require(value==m['collection'],'Retained phase reconstruction differs')
    require(value['run_identity']==str(m['application_run'])+':'+str(m['run_attempt']),'Phase run differs')
    return value
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifest');a=p.parse_args();v=verify(a.manifest);print(json.dumps({'mode':v['mode'],'units':len(v['records']),'qualified':v['all_units_qualified']}))
