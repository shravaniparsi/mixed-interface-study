"""Synthetic Docker metadata tests; no container/network execution."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/extension'))
import provision_nginx_ordinary_v1 as m

class TopologyTests(unittest.TestCase):
    def fixture(self):
        roots={'/data':Path('/private/data'),'/etc/letsencrypt':Path('/private/certificates')}
        def container(identity,image,ip):
            return dict(Id=identity,Image=image,State={'Running':True,'Paused':False,'Restarting':False,'Dead':False},Config={'Labels':{m.LABEL:m.VALUE}},
                HostConfig={'Privileged':False,'PortBindings':{},'PublishAllPorts':False,'RestartPolicy':{'Name':'no'}},
                NetworkSettings={'Networks':{m.NETWORK:{'IPAddress':ip,'NetworkID':'network'}}},Mounts=[])
        app=container('app','sha256:application','172.28.0.2');browser=container('browser',m.BROWSER_ID,'172.28.0.3')
        app['Mounts']=[{'Destination':k,'Source':str(v),'Type':'bind','RW':True} for k,v in roots.items()]
        network=dict(Id='network',Internal=True,Driver='bridge',EnableIPv6=False,IPAM={'Config':[{'Subnet':'172.28.0.0/24','Gateway':'172.28.0.1'}]},Containers={'app':{},'browser':{}})
        return network,app,browser,'sha256:application',roots
    def test_registered_topology(self):
        self.assertTrue(m.verify_topology(*self.fixture())['internal'])
    def test_egress_and_extra_participants_rejected(self):
        for key,value in [('Internal',False),('EnableIPv6',True),('Containers',{'app':{},'browser':{},'other':{}})]:
            args=list(self.fixture());args[0][key]=value
            with self.assertRaises(ValueError):m.verify_topology(*args)
    def test_ports_privileges_and_restart_rejected(self):
        for key,value in [('PortBindings',{'81/tcp':[{'HostPort':'8081'}]}),('PublishAllPorts',True),('Privileged',True),('RestartPolicy',{'Name':'always'})]:
            args=list(self.fixture());args[1]['HostConfig'][key]=value
            with self.assertRaises(ValueError):m.verify_topology(*args)
    def test_wrong_images_addresses_and_network_rejected(self):
        for mutation in ('image','ip','network','extra'):
            args=list(self.fixture());b=args[2]
            if mutation=='image': b['Image']='other'
            elif mutation=='ip': b['NetworkSettings']['Networks'][m.NETWORK]['IPAddress']='172.28.0.9'
            elif mutation=='network': b['NetworkSettings']['Networks'][m.NETWORK]['NetworkID']='other'
            else:b['NetworkSettings']['Networks']['external']={}
            with self.assertRaises(ValueError):m.verify_topology(*args)
    def test_exited_or_paused_container_rejected(self):
        for key,value in [('Running',False),('Paused',True),('Restarting',True),('Dead',True)]:
            args=list(self.fixture());args[1]['State'][key]=value
            with self.assertRaises(ValueError):m.verify_topology(*args)
    def test_state_mount_identity_and_writability_required(self):
        for key,value in [('Source','/other'),('Type','volume'),('RW',False)]:
            args=list(self.fixture());args[1]['Mounts'][0][key]=value
            with self.assertRaises(ValueError):m.verify_topology(*args)

if __name__=='__main__':unittest.main()
