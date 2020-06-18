import unittest
import ngc
import tempfile
import os
from distutils.dir_util import copy_tree

class IntegrationTest(unittest.TestCase):
    TEST_DIR = os.path.join(os.getcwd(),'test/test_dir')

    def test_init(self):

        with tempfile.TemporaryDirectory() as temp_dir:
            copy_tree(self.TEST_DIR, temp_dir)
            #dir_path = os.path.join(temp_dir, 'test/test_dir')
            ngc_obj = ngc.Ngc(repo_path=temp_dir)
            ngc_obj.init()
            ngc_path = os.path.join(ngc_obj.repo_path, ".ngc")
            objects_path = os.path.join(ngc_obj.repo_path, ".ngc/objects")

            self.assertTrue(os.path.exists(ngc_path))
            self.assertTrue(os.path.exists(objects_path))

    def test_commit(self):

        with tempfile.TemporaryDirectory() as temp_dir:
            copy_tree(self.TEST_DIR, temp_dir)

            ngc_obj = ngc.Ngc(repo_path=temp_dir)
            ngc_obj.init()
            ngc_obj.commit(message="test commit")

            with open(ngc_obj.repo_path+"/.ngc/HEAD", "r") as head_file:
                commit_hash = head_file.read()
            self.assertEqual(commit_hash, '3b3224307230833a3538f03fb7ae5c4dade57809')

if __name__ == "__main__":
    unittest.main()
