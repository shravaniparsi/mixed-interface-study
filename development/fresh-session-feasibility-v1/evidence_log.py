"""Transport completed sanitized exports in Actions logs; never read private raw evidence."""
import base64,hashlib,json,pathlib,re,sys,zlib
from source_check import require
LIMIT=40*1024**2
PREFIX='FRESH_EVIDENCE_V1 '
def encode(directory):
 directory=pathlib.Path(directory);require(not (directory/'EXPORT_FAILED').exists(),'export_completed')
 report=json.loads((directory/'export.json').read_text());require(report['status']=='sanitized','sanitized_export_required')
 names=['export.json']+[row['file'] for row in report['files']];require(len(set(names))==len(names),'unique_export_names');files={}
 for name in names:
  require(pathlib.Path(name).name==name and name not in {'.','..'},'safe_export_name')
  p=directory/name;require(p.is_file() and not p.is_symlink(),'regular_export_file');files[name]=p.read_text()
 for row in report['files']:require(hashlib.sha256(files[row['file']].encode()).hexdigest()==row['public_sha256'],'export_digest')
 raw=json.dumps(files,separators=(',',':')).encode();require(len(raw)<=LIMIT,'log_transport_size')
 payload=base64.b64encode(zlib.compress(raw,9)).decode();parts=[payload[i:i+12000] for i in range(0,len(payload),12000)]
 return '\n'.join([PREFIX+str(i)+' '+part for i,part in enumerate(parts)]+[PREFIX+'END '+str(len(parts))+' '+hashlib.sha256(raw).hexdigest()])+'\n'
def decode(log):
 parts=[];end=None
 for line in log.splitlines():
  marker=line.find(PREFIX)
  if marker<0:continue
  match=re.fullmatch(r'(\d+) ([A-Za-z0-9+/=]+)',line[marker+len(PREFIX):])
  if match:
   require(end is None and int(match[1])==len(parts),'ordered_complete_chunks');parts.append(match[2]);continue
  match=re.fullmatch(r'END (\d+) ([a-f0-9]{64})',line[marker+len(PREFIX):]);require(match is not None and end is None,'single_transport_end');end=match.groups()
 require(end is not None and len(parts)==int(end[0]),'transport_complete');require(sum(map(len,parts))<=2*LIMIT,'encoded_size_cap')
 inflater=zlib.decompressobj();raw=inflater.decompress(base64.b64decode(''.join(parts),validate=True),LIMIT+1)
 require(len(raw)<=LIMIT and inflater.eof and not inflater.unused_data,'bounded_complete_decompression');require(hashlib.sha256(raw).hexdigest()==end[1],'transport_digest')
 files=json.loads(raw);require(isinstance(files,dict),'transport_files')
 for name,content in files.items():require(pathlib.Path(name).name==name and name not in {'.','..'} and isinstance(content,str),'safe_transport_file')
 return files
if __name__=='__main__':
 if sys.argv[1]=='emit':sys.stdout.write(encode(sys.argv[2]))
 elif sys.argv[1]=='recover':
  files=decode(pathlib.Path(sys.argv[2]).read_text());dest=pathlib.Path(sys.argv[3]);dest.mkdir(exist_ok=False)
  for name,content in files.items():(dest/name).write_text(content)
 else:raise ValueError('unknown mode')
