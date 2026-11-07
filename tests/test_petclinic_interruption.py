"""Ownership accounting tests; live application qualification runs in manual CI."""
import importlib.util
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/ci'))
from run_petclinic_interruption import track,survivors


def p(pid,parent,start='1',state='S'):
    return {'pid':pid,'ppid':parent,'start_ticks':start,'state':state,'command':'fixture'}


class InterruptionOwnershipTests(unittest.TestCase):
    def test_descendants_include_detached_group_children_by_parentage(self):
        table={1:p(1,0),2:p(2,1),3:p(3,2),4:p(4,99)}
        self.assertEqual(set(track(table,1,{})),{2,3})

    def test_known_reparented_descendant_stays_owned(self):
        known={2:p(2,1)}
        self.assertEqual(set(track({2:p(2,999),3:p(3,2)},1,known)),{2,3})

    def test_reused_pid_does_not_authorize_new_descendants(self):
        known={2:p(2,1,'old')}
        table={2:p(2,999,'new'),3:p(3,2)}
        self.assertEqual(set(track(table,1,known)),{2})
        self.assertEqual(survivors(table,known),[])

    def test_zombies_and_exited_processes_are_not_live_survivors(self):
        known={2:p(2,1),3:p(3,2),4:p(4,2)}
        table={2:p(2,1,state='Z'),3:p(3,2)}
        self.assertEqual([v['pid'] for v in survivors(table,known)],[3])

    def test_unrelated_processes_are_never_owned(self):
        table={10:p(10,99),11:p(11,10)}
        self.assertEqual(track(table,1,{}),{})
