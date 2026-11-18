import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from seatsurfing_tree_identity_v2 import root_tree_sha

class TreeIdentity(unittest.TestCase):
    def test_original_git_object_encoding_and_directory_sort(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'a').mkdir();(root/'a'/'z').write_text('nested')
            (root/'a.c').write_text('first');(root/'a0').write_text('last');(root/'a-link').symlink_to('a/z')
            def git(*args):return subprocess.check_output(['git','-C',directory,*args],stderr=subprocess.DEVNULL).decode().strip()
            git('init','-q');git('add','.');tree=git('write-tree')
            entries=[]
            for line in git('ls-tree','-r','-t',tree).splitlines():
                metadata,path=line.split('\t');mode,kind,sha=metadata.split()
                entries.append({'mode':mode,'type':kind,'sha':sha,'path':path})
            self.assertEqual(root_tree_sha(entries),tree)
            changed=copy.deepcopy(entries);next(row for row in changed if row['path']=='a/z')['sha']='0'*40
            with self.assertRaisesRegex(ValueError,'Recursive'):root_tree_sha(changed)
    def test_retained_seatsurfing_tree_is_internally_consistent(self):
        path=Path(__file__).resolve().parents[2]/'results/catalog-application-metadata-v1/09/3.json'
        data=json.loads(path.read_text());actual=root_tree_sha(data['tree'])
        self.assertEqual(len(actual),40)
        self.assertNotEqual(actual,data['sha'])
    def test_missing_parent_rejected(self):
        with self.assertRaisesRegex(ValueError,'parent'):root_tree_sha([{'path':'a/b','mode':'100644','type':'blob','sha':'0'*40}])

if __name__=='__main__':unittest.main()
