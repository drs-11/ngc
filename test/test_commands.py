import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from distutils.dir_util import copy_tree
from pathlib import Path
from io import StringIO

from ngc import commands


class InitTest(unittest.TestCase):

    def test_init_without_config(self):

        with tempfile.TemporaryDirectory() as temp_dir:
            copy_tree('./test/test_dir/', temp_dir)
            cmd = commands.Command(temp_dir)
            output = StringIO()
            print(cmd.user_details)
            with redirect_stdout(output):
                cmd.init()
            expected_output = "Please configure user settings through config command first!\n"
            self.assertEqual(output.getvalue(), expected_output)

    def test_init_user_configured(self):

        with tempfile.TemporaryDirectory() as temp_dir:
            copy_tree('./test/test_dir/', temp_dir)
            test_user_deets = {
                'user_name': '<somegenericusername>',
                'user_email': '<somegenericemail>',
                'timestamp': 0,
            }
            info_file_path = os.path.join(str(Path.home()), ".userinfo")    # TODO: need to make this isolated
            with open(info_file_path, 'w') as user_file:
                json.dump(test_user_deets, user_file)
            # copy_tree('./test/test_dir/', temp_dir)
            cmd = commands.Command(temp_dir)
            cmd.init()
            
            ngc_path = os.path.join(cmd.repo_path, ".ngc")
            objects_path = os.path.join(cmd.repo_path, ".ngc/objects")

            self.assertTrue(os.path.exists(ngc_path))
            self.assertTrue(os.path.exists(objects_path))

            os.remove(info_file_path)


class CommitTest(unittest.TestCase):

    def test_first_commit(self):

        with tempfile.TemporaryDirectory() as temp_dir:
            copy_tree('./test/test_dir/', temp_dir)

            cmd = commands.Command(temp_dir)
            cmd.config_user('<genericname>', '<genericemail>')
            cmd.init()
            cmd.commit("first commit")

            tree_file_path = os.path.join(cmd.obj_tree.objects_path, "0fbd657ff0d946213275023ae722c244c3026682")
            self.assertTrue(os.path.exists(tree_file_path))
            self.assertEqual(cmd.obj_tree.current_tree_hash, "0fbd657ff0d946213275023ae722c244c3026682")

    def test_commit_with_file_modification(self):
        
        with tempfile.TemporaryDirectory() as temp_dir:
            copy_tree('./test/test_dir/', temp_dir)

            cmd = commands.Command(temp_dir)
            cmd.config_user('<genericname>', '<genericemail>')
            cmd.init()
            cmd.commit("first commit")

            with open(temp_dir + '/file1', 'a') as file1:
                file1.write("An addition.\n")

            cmd.commit("second commit with modification")

            tree_file_path = os.path.join(cmd.obj_tree.objects_path, "7b58e3728ac207ec2ff18f8e374688b893eaed4f")
            self.assertTrue(os.path.exists(tree_file_path))
            self.assertEqual(cmd.obj_tree.current_tree_hash, "7b58e3728ac207ec2ff18f8e374688b893eaed4f")

    def test_commit_with_file_deletion(self):

        with tempfile.TemporaryDirectory() as temp_dir:
            copy_tree('./test/test_dir/', temp_dir)

            cmd = commands.Command(temp_dir)
            cmd.config_user('<genericname>', '<genericemail>')
            cmd.init()
            cmd.commit("first commit")

            os.remove(temp_dir + '/file1')

            cmd.commit("second commit with file deletion")

            tree_file_path = os.path.join(cmd.obj_tree.objects_path, "1ee7866845063cea765805d6bee24b964cc3505d")
            self.assertTrue(os.path.exists(tree_file_path))
            self.assertEqual(cmd.obj_tree.current_tree_hash, "1ee7866845063cea765805d6bee24b964cc3505d")

    def test_commit_without_changes(self):

        with tempfile.TemporaryDirectory() as temp_dir:
            copy_tree('./test/test_dir/', temp_dir)

            cmd = commands.Command(temp_dir)
            cmd.config_user('<genericname>', '<genericemail>')
            cmd.init()
            cmd.commit("first commit")

            output = StringIO()
            with redirect_stdout(output):
                cmd.commit("second commit with no changes")
            
            self.assertEqual(output.getvalue(), "No changes detected, nothing to commit.\n")