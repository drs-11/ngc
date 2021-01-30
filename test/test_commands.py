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

    def test_init_vanilla(self):

        with tempfile.TemporaryDirectory() as temp_dir:
            copy_tree('./test/test_dir/', temp_dir)
            cmd = commands.Command(temp_dir)
            output = StringIO()
            with redirect_stdout(output):
                cmd.init()
            expected_output = "Please configure user settings through config command first!"
            self.assertTrue(output, expected_output)

    def test_init_user_configured(self):

        with tempfile.TemporaryDirectory() as temp_dir:
            copy_tree('./test/test_dir/', temp_dir)
            test_user_deets = {
                'user_name': '<somegenericusername>',
                'user_email': '<somegenericemail>',
                'timestamp': 0,
            }
            info_file_path = os.path.join(str(Path.home()), ".userinfo")
            with open(info_file_path, 'w') as user_file:
                json.dump(test_user_deets, user_file)
            copy_tree('./test/test_dir/', temp_dir)
            cmd = commands.Command(temp_dir)
            
            ngc_path = os.path.join(cmd.repo_path, ".ngc")
            objects_path = os.path.join(cmd.repo_path, ".ngc/objects")

            self.assertTrue(os.path.exists(ngc_path))
            self.assertTrue(os.path.exists(objects_path))

            os.remove(info_file_path)

