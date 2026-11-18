"""Synthetic observations only; no live restart qualification."""
from copy import deepcopy
import hashlib
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/extension'))
import nginx_restart_state_comparison_v1 as m
from nginx_ordinary_filesystem_delta_v1 import ROOTS

class RestartStateTests(unittest.TestCase):
    def fixture(self):
        def row(path,kind='directory',raw=b''):
            r=dict(path=path,kind=kind,uid=1001,gid=1001,mode=493 if kind=='directory' else 420,mtimeNs='1000000000')
            if kind=='file': r.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
            return r
        a=dict(status='runtime_observation_only_not_atomic_or_qualified',extendedAttributesAbsent=True,
               inventories={r:[row('.')] for r in ROOTS},environment={'fixed':'same'},
               backend=dict(pid=10,startTicks='1',executable='/usr/bin/node',executableSha256='node',uid=1001,gid=1001,argv=['node','index.js'],cwd='/app'),
               master=dict(pid=20,startTicks='2',executable='/usr/sbin/nginx',executableSha256='nginx',uid=1001,gid=1001,argv=['nginx'],cwd='/'))
        a['inventories']['/data'] += [row('database.sqlite','file',b'db'),row('keys.json','file',b'key')]
        a['inventories']['/etc/nginx'] += [row('conf.d'),row('conf.d/production.conf','file',b'peerA'),row('conf.d/default.conf','file',b'fixed')]
        a['inventories']['/run/nginx'] += [row('nginx.pid','file',b'20\n')]
        a['peer']=dict(backendSecretMatches=True,adminPort=81,disableIpv6=True,backendPid=10,configurationSha256=hashlib.sha256(b'peerA').hexdigest(),templateSha256='template',normalizedConfigurationSha256='normalized')
        b=deepcopy(a);b['backend'].update(pid=11,startTicks='3');b['master'].update(pid=21,startTicks='4');b['peer'].update(backendPid=11,configurationSha256=hashlib.sha256(b'peerB').hexdigest())
        for root,path,raw in [('/etc/nginx','conf.d/production.conf',b'peerB'),('/run/nginx','nginx.pid',b'21\n')]:
            r=next(r for r in b['inventories'][root] if r['path']==path);r.update(sha256=hashlib.sha256(raw).hexdigest(),mtimeNs='2000000000')
        return a,b,dict(timezone='UTC',start_epoch_seconds=1.5,end_epoch_seconds=2.5)
    def check(self,a,b,w,left=None,right=None):
        return m.compare_restart_state(a,b,{} if left is None else left,{} if right is None else right,w)
    def test_bound_peer_and_pid_restart(self):
        a,b,w=self.fixture();self.assertEqual(len(self.check(a,b,w)['changes']),2)
    def test_only_mtime_admitted_for_rewritten_conf(self):
        a,b,w=self.fixture();r=b['inventories']['/etc/nginx'][-1];r['mtimeNs']='2000000000';self.check(a,b,w)
        r['sha256']='changed'
        with self.assertRaisesRegex(ValueError,'Unexplained'):self.check(a,b,w)
    def test_no_credential_or_log_normalization(self):
        for root in ('/data','/var/log/nginx'):
            a,b,w=self.fixture();b['inventories'][root][-1]['mode']=511
            with self.assertRaises(ValueError):self.check(a,b,w)
    def test_exact_database_required(self):
        a,b,w=self.fixture()
        with self.assertRaisesRegex(ValueError,'database differs'):self.check(a,b,w,{'rows':[1]},{'rows':[2]})
    def test_peer_proof_must_bind_actual_file_and_backend(self):
        for key,value in [('configurationSha256','wrong'),('backendPid',77),('normalizedConfigurationSha256','different')]:
            a,b,w=self.fixture();b['peer'][key]=value
            with self.assertRaises(ValueError):self.check(a,b,w)
    def test_pid_proof_and_executable_change_rejected(self):
        for key,value in [('pid',99),('executableSha256','changed')]:
            a,b,w=self.fixture();b['master'][key]=value
            with self.assertRaises(ValueError):self.check(a,b,w)
    def test_stale_timestamp_and_added_file_rejected(self):
        a,b,w=self.fixture();b['inventories']['/etc/nginx'][-2]['mtimeNs']='3000000000'
        with self.assertRaisesRegex(ValueError,'timestamp'):self.check(a,b,w)
        a,b,w=self.fixture();b['inventories']['/data'].append(dict(b['inventories']['/data'][-1],path='surprise'))
        with self.assertRaisesRegex(ValueError,'added'):self.check(a,b,w)

if __name__=='__main__':unittest.main()
