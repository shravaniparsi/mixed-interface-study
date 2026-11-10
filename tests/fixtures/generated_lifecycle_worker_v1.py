"""Synthetic worker: no network, browser, application or child processes."""
import json,shutil,sys,time
from pathlib import Path
source,output,mode=map(str,sys.argv[1:]);source=Path(source);output=Path(output)
shutil.copyfile(source/'fixture.bin',output/'reset.bin')
if mode=='timeout':time.sleep(60)
if mode=='failure':raise SystemExit(7)
raw=json.loads((source/'raw.json').read_bytes())
(output/'raw.json').write_text(json.dumps(raw))
