"""Acquire a frozen source schedule with bounded reads and exact Git blob checks."""
import hashlib,json,pathlib,sys,urllib.request
manifest=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);out.mkdir(exist_ok=False)
m=json.loads(manifest.read_text());records=[];total=0
for row in m['rows']:
 for f in row['files']:
  rec=dict(sequence=row['sequence'],repository=row['repository'],revision=row['revision'],**f);records.append(rec)
  try:
   assert f['bytes']<=m['max_file_bytes']
   url=f"https://raw.githubusercontent.com/{row['repository']}/{row['revision']}/{f['path']}"
   with urllib.request.urlopen(url,timeout=30) as response:raw=response.read(m['max_file_bytes']+1)
   total+=len(raw);assert len(raw)==f['bytes'] and total<=m['max_total_bytes']
   assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==f['blob']
   name=str(row['sequence'])+'--'+f['path'].replace('/','--');(out/name).write_bytes(raw)
   rec.update(status='verified',sha256=hashlib.sha256(raw).hexdigest(),local_filename=name)
  except Exception as e:rec.update(status='unavailable',error_type=type(e).__name__,error=str(e))
receipt=dict(schedule_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),rows=records,total_bytes=total)
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(files=len(records),verified=sum(x['status']=='verified' for x in records),total_bytes=total)))
