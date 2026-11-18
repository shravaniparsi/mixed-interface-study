import unittest
from seatsurfing_fixture_resources_v1 import verify_inventory, PG, APP, LABEL_KEY, LABEL_VALUE


def item(name,identity,network,label=True):
    return {'Name':'/'+name,'Id':identity,'Config':{'Labels':{LABEL_KEY:LABEL_VALUE} if label else {}},'HostConfig':{'NetworkMode':network}}


class Resources(unittest.TestCase):
    def test_exact_owned_fixture_and_unrelated_container(self):
        owned=verify_inventory([item(PG,'pg-id','none'),item(APP,'app-id','container:pg-id'),item('unrelated','other','bridge',False)])
        self.assertEqual(set(owned),{PG,APP})
    def test_unlabelled_collision_is_not_cleaned(self):
        with self.assertRaisesRegex(ValueError,'ownership'):verify_inventory([item(APP,'foreign','none',False)])
    def test_unknown_labelled_resource_is_not_silently_deleted(self):
        with self.assertRaisesRegex(ValueError,'Unexpected'):verify_inventory([item('unknown-study-client','other','none')])
    def test_unregistered_direct_namespace_client_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unregistered'):verify_inventory([item(PG,'pg-id','none'),item('unknown','other','container:pg-id',False)])
    def test_indirect_namespace_client_rejected(self):
        # Deliberately list child before its parent to test transitive closure.
        with self.assertRaisesRegex(ValueError,'Unregistered'):verify_inventory([item('unknown','other','container:app-id',False),item(APP,'app-id','container:pg-id'),item(PG,'pg-id','none')])


if __name__=='__main__':unittest.main()
