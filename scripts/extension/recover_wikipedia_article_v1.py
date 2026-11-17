#!/usr/bin/env python3
"""Bounded, resumable range reader for the frozen May 2022 ZIM article.
Layout checked against openzim/libzim ad888b4. Not a general ZIM reader.
"""
import hashlib,json,lzma,pathlib,struct,urllib.request,sys
ROOT=pathlib.Path('results/benchmark-wikipedia-article-v1')
URL='https://huggingface.co/datasets/Atesting1/webarena-env/resolve/d28451f44a6a05ed753fede8c70b0be91c0239d0/wikipedia_en_all_maxi_2022-05.zim'
SIZE=95199730590
CAP=32*1024*1024

def save(log):
    (ROOT/'retrieval.json').write_text(json.dumps(log,indent=2)+'\n')

def fetch(start,n,log):
    assert 0<=start<start+n<=SIZE
    for r in log['ranges']:
        if r['start']==start and r['length']==n and r.get('verified'):
            b=(ROOT/r['file']).read_bytes()
            assert len(b)==n and hashlib.sha256(b).hexdigest()==r['sha256']
            return b
    assert '--offline' not in sys.argv,'offline cache miss'
    assert all(r.get('verified') for r in log['ranges']),'prior failed request; stop'
    assert len(log['ranges'])+1<64,'request cap (includes original header probe)'
    assert sum(r['length'] for r in log['ranges'])+n+80<=16*1024*1024,'transfer cap'
    r={'start':start,'length':n};log['ranges'].append(r);save(log)
    req=urllib.request.Request(URL,headers={'Range':f'bytes={start}-{start+n-1}','Accept-Encoding':'identity'})
    with urllib.request.urlopen(req,timeout=45) as resp:
        r.update(status=resp.status,content_range=resp.headers.get('Content-Range'))
        save(log)
        assert resp.status==206 and r['content_range']==f'bytes {start}-{start+n-1}/{SIZE}','range mismatch'
        assert resp.headers.get('Content-Encoding','identity')=='identity'
        b=resp.read(n+1)
    assert len(b)==n,'body length mismatch'
    r.update(file=f'range-{start}-{n}.bin',sha256=hashlib.sha256(b).hexdigest(),verified=True)
    (ROOT/r['file']).write_bytes(b);save(log)
    return b

def run(log):
    h=pathlib.Path('results/benchmark-wikipedia-range-feasibility-v1/header.bin').read_bytes()
    assert hashlib.sha256(h).hexdigest()=='35a90759c739a8ac9774f3d0ceba5953361893f10f89e20db6022e5e6f16cc7b'
    count,clusters=struct.unpack_from('<II',h,24)
    ptr,title,clptr=struct.unpack_from('<QQQ',h,32)
    def entry(i):
        assert 0<=i<count
        off=struct.unpack('<Q',fetch(ptr+8*i,8,log))[0]
        b=fetch(off,1024,log)
        mime,extra,ns,version=struct.unpack_from('<HBBI',b)
        cluster,blob=struct.unpack_from('<II',b,8) if mime<65533 else (None,None)
        offset=12 if mime==65535 else 8 if mime>=65533 else 16
        path,caption,rest=b[offset:].split(b'\0',2)
        assert len(rest)>=extra
        return bytes([ns])+b'/'+path,cluster,blob,caption
    target=b'A/Christopher_Nolan';lo,hi=0,count
    found=None
    while lo<hi:
        mid=(lo+hi)//2;e=entry(mid)
        print(mid,e[0].decode(errors='replace'),flush=True)
        if e[0]==target:found=e;break
        if e[0]<target:lo=mid+1
        else:hi=mid
    assert found is not None,'selected article missing'
    key,c,b,title=found
    assert c is not None,'selected entry is redirect/deleted; stop'
    assert c+1<clusters,'last cluster unsupported'
    start,end=struct.unpack('<QQ',fetch(clptr+8*c,16,log))
    log['entry']={'key':key.decode(),'cluster':c,'blob':b,'cluster_start':start,'cluster_end':end};save(log)
    raw=fetch(start,end-start,log);comp=raw[0]&15
    log['compression']=comp;save(log)
    if comp in (0,1):data=raw[1:];assert len(data)<=CAP
    elif comp==4:
        dec=lzma.LZMADecompressor(memlimit=CAP)
        data=dec.decompress(raw[1:],max_length=CAP+1)
        assert len(data)<=CAP and dec.eof and not dec.unused_data,'decompression cap or incomplete stream'
    elif comp==5:
        import zstandard
        # Streaming read caps output even when frame size metadata is absent.
        import io
        assert zstandard.get_frame_parameters(raw[1:]).window_size<=CAP
        with zstandard.ZstdDecompressor(max_window_size=CAP).stream_reader(io.BytesIO(raw[1:])) as reader:
            data=reader.read(CAP+1)
        assert len(data)<=CAP,'decompression cap'
    else:raise ValueError('unsupported compression')
    fmt='<Q' if raw[0]&16 else '<I';width=struct.calcsize(fmt)
    first=struct.unpack_from(fmt,data)[0]
    assert first%width==0 and 2*width<=first<=len(data)
    offsets=[x[0] for x in struct.iter_unpack(fmt,data[:first])]
    assert offsets==sorted(offsets) and offsets[-1]==len(data) and b+1<len(offsets)
    article=data[offsets[b]:offsets[b+1]]
    article.decode('utf-8')
    (ROOT/'Christopher_Nolan.html').write_bytes(article)
    log.pop('error',None)
    log.update(status='recovered',article_sha256=hashlib.sha256(article).hexdigest(),article_bytes=len(article),decompressed_bytes=len(data))

if __name__=='__main__':
    ROOT.mkdir(parents=True,exist_ok=True)
    log=json.loads((ROOT/'retrieval.json').read_text()) if (ROOT/'retrieval.json').exists() else {'url':URL,'ranges':[],'limits':{'requests':64,'transfer_bytes':16777216,'decompressed_bytes':CAP}}
    try:run(log)
    except Exception as e:
        log.update(status='stopped',error=type(e).__name__+': '+str(e));raise
    finally:save(log)
