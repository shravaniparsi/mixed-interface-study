"""Audit current available tracked text references for fixed remainder candidates."""
import collections, hashlib, json, pathlib, subprocess
ROOT=pathlib.Path(__file__).resolve().parents[2]
def main():
 old=json.loads((ROOT/'manifests/redesign-evaluation-exposure-v1.json').read_text())
 rows=[dict(x) for x in old['rows'] if x['sequence']>=20]
 files=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
 counts=collections.Counter();refs={r['repository']:[] for r in rows}
 for name in files:
  if not name:continue
  p=ROOT/name
  if not p.is_file():counts['missing']+=1;continue
  if p.stat().st_size>4*1024*1024:counts['oversized']+=1;continue
  raw=p.read_bytes()
  try:text=raw.decode('utf-8').lower()
  except UnicodeDecodeError:counts['non_utf8']+=1;continue
  counts['scanned']+=1
  for repo in refs:
   if repo.lower() in text:refs[repo].append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest()))
 for r in rows:
  base=ROOT/'results/editability-repairability-repository-metadata-v1'/str(r['sequence'])
  meta=json.loads((base/'1.json').read_text());ref=json.loads((base/'2.json').read_text());tree=json.loads((base/'3.json').read_text())
  assert meta['full_name'].lower()==r['repository'].lower()
  assert ref['object']['sha']==r['revision']
  r.update(current_reference_files=refs[r['repository']],github_fork=meta['fork'],parent=(meta.get('parent') or {}).get('full_name'),tree_complete=not tree['truncated'],metadata_sha256={str((base/n).relative_to(ROOT)):hashlib.sha256((base/n).read_bytes()).hexdigest() for n in ['1.json','2.json','3.json']},independence_established=False,admitted=False)
 return dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),rows=rows,current_scan_counts=dict(counts),historical_gaps=old['history_gaps'],scope='Exact repository-string references in available tracked UTF-8 files <=4MiB. Not alias/lineage proof; current metadata is previously acquired pinned metadata, not live revalidation.',new_application_source_reads=0)
if __name__=='__main__':print(json.dumps(main(),indent=2))
