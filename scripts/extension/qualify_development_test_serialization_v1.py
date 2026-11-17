#!/usr/bin/env python3
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/development-test-serialization-v1'
WORK = Path('/private/tmp/development-test-serialization-v1')
JAR = Path('/private/tmp/development-spec-build-v1-binary/application.jar')
NAMES = ['testRegisterValid','testRegisterInvalidLogin','testRegisterInvalidEmail','testRegisterInvalidPassword','testRegisterNullPassword']
def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def main():
    assert not OUT.exists() and not WORK.exists(), 'Closed run cannot be overwritten'
    OUT.mkdir(); WORK.mkdir()
    result = {'kind':'original_test_fixture_serialization', 'rows':[{'id':n,'status':'not_run'} for n in NAMES], 'errors':[], 'commands':[], 'independent_evaluation_cases':0,'application_requests':0}
    start = time.monotonic()
    def command(args, timeout):
        r = subprocess.run(args,capture_output=True,text=True,timeout=timeout,cwd=WORK)
        result['commands'].append({'args':args,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
        if r.returncode: raise RuntimeError('Command failed: '+args[0])
        return r.stdout+r.stderr
    try:
        jarraw=JAR.read_bytes()
        assert sha(jarraw)=='1c7500685740eb01994aa13ea381f3eb9af2c65bfb92f2379e42bb909225c71b'
        result['jar_sha256']=sha(jarraw)
        source=Path('/private/tmp/development-assertion-source-v1/3.txt').read_bytes()
        record=json.loads((ROOT/'manifests/development-assertion-source-v1.json').read_text())['rows'][2]
        assert sha(source)==record['sha256']
        helper=Path('/private/tmp/development-assertion-setup-v1/1.txt').read_bytes()
        assert sha(helper)=='132ed1ac957f90b8e0b8dc1cfe458fa8e86bf9d30ee53b6e8330de9fe6eae5b1'
        result['source_sha256']=sha(source);result['helper_sha256']=sha(helper)
        java_version=command(['java','-version'],10); compiler_version=command(['javac','-version'],10)
        assert '19.0.1' in java_version and '19.0.1' in compiler_version
        result['java_version']=java_version.strip();result['compiler_version']=compiler_version.strip()
        with zipfile.ZipFile(JAR) as z:
            for info in z.infolist():
                if info.is_dir() or not info.filename.startswith(('BOOT-INF/classes/','BOOT-INF/lib/')):continue
                path=WORK/info.filename
                assert path.resolve().is_relative_to(WORK.resolve())
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(info))
        imports='''import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import java.io.IOException;
import java.util.Collections;
import java.util.Base64;
import org.jhipster.health.web.rest.vm.ManagedUserVM;
import org.jhipster.health.config.Constants;
import org.jhipster.health.security.AuthoritiesConstants;
'''
        methods=[]
        for signature in ['private static ObjectMapper createObjectMapper()', 'public static byte[] convertObjectToJsonBytes(Object object) throws IOException']:
            text=helper.decode();p=text.index(signature);end=text.index('\n    }',p)+len('\n    }');methods.append(text[p:end])
        blocks=[]
        for name in NAMES:
            text=source.decode();p=text.index('void '+name+'()');tail=text[p:]
            match=re.search(r'(ManagedUserVM (\w+) = new ManagedUserVM\(\);[\s\S]*?)(?=\n\s*(?:assertThat|restAccountMockMvc))',tail)
            assert match, name
            fixture,var=match.group(1),match.group(2)
            blocks.append('{\n'+fixture+'\nSystem.out.println("'+name+'\\t" + Base64.getEncoder().encodeToString(convertObjectToJsonBytes('+var+')));\n}')
        wrapper=imports+'public class SerializationProbe {\nprivate static final ObjectMapper mapper=createObjectMapper();\n'+'\n'.join(methods)+'\npublic static void main(String[] args) throws Exception {\n'+'\n'.join(blocks)+'\n}\n}\n'
        (WORK/'SerializationProbe.java').write_text(wrapper)
        (OUT/'SerializationProbe.java').write_text(wrapper)
        result['wrapper_sha256']=sha(wrapper.encode())
        classpath=str(WORK/'BOOT-INF/classes')+':'+str(WORK/'BOOT-INF/lib/*')
        command(['javac','-cp',classpath,'SerializationProbe.java'],60)
        raw=command(['java','-cp',str(WORK)+':'+classpath,'SerializationProbe'],30)
        lines=raw.splitlines();assert len(lines)==len(NAMES)
        for row,line in zip(result['rows'],lines):
            name,data=line.split('\t');assert name==row['id']
            body=base64.b64decode(data,validate=True);document=json.loads(body)
            row.update(status='serialized',body=document,body_sha256=sha(body),password_presence='present' if 'password' in document else 'absent')
    except Exception as e:
        result['errors'].append({'type':type(e).__name__,'message':str(e)})
    result['elapsed_seconds']=time.monotonic()-start
    (OUT/'measurement.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'rows':len(result['rows']),'serialized':sum(r['status']=='serialized' for r in result['rows']),'errors':result['errors']}))
    return int(bool(result['errors']))

if __name__=='__main__':
    raise SystemExit(main())
