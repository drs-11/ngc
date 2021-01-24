import gzip
import os
import tempfile
import unittest
from distutils.dir_util import copy_tree

from ngc import objects


class BlobTest(unittest.TestCase):
    
    def setUp(self):
        self.blob = objects.Blob()
        self.data_to_compressed = {
            'HAPPY': b'\x1f\x8b\x08\x00\xa0\xd3\x0b`\x02\xffK\xca\xc9OR0e\xf0p\x0c\x08\x88\x04\x00\x1f\x98\xbd;\x0c\x00\x00\x00',
            'SAD': b'\x1f\x8b\x08\x00\xfb\xd5\x0b`\x02\xffK\xca\xc9OR0f\x08vt\x01\x00\x14\x8d)\x8e\n\x00\x00\x00',
            'CONSTIPATED': b'\x1f\x8b\x08\x00\x10\xd6\x0b`\x02\xffK\xca\xc9OR04dp\xf6\xf7\x0b\x0e\xf1\x0cp\x0cqu\x01\x00tV\xe9\xcf\x13\x00\x00\x00',
        }
        self.data_to_hashed_name = {
            'HAPPY': '3893628b684f4db632974cf6b90097ef1cf4fe88',
            'SAD': '8747bd7070ef19d99083a3bde89d303d95e66d23',
            'CONSTIPATED': '7a9a8d063022102aad43b487a8fe7dc647c8f567',
        }

    def test_get_header(self):

        for data, compressed in self.data_to_compressed.items():
            with tempfile.NamedTemporaryFile() as src_file:
                src_file.write(compressed)
                src_file.seek(0)
                header = self.blob.get_header(src_file.name)
                expected_header = "blob %d\x00" % len(data)
                self.assertEqual(header, expected_header)

    def test_get_content(self):

        for data, compressed in self.data_to_compressed.items():
            with tempfile.NamedTemporaryFile() as src_file:
                src_file.write(compressed)
                src_file.seek(0)
                content = self.blob.get_content(src_file.name)
                self.assertEqual(data, content)

    def test_extract_content(self):

        for data, compressed in self.data_to_compressed.items():
            with tempfile.NamedTemporaryFile() as src_file:
                with tempfile.NamedTemporaryFile() as dst_file:
                    src_file.write(compressed)
                    src_file.seek(0)
                    self.blob.extract_content(src_file.name, dst_file.name)
                    dst_file.seek(0)
                    self.assertEqual(data.encode(), dst_file.read())

    def test_get_file_hash(self):

        for data, expected_hash in self.data_to_hashed_name.items():
            with tempfile.NamedTemporaryFile() as src_file:
                src_file.write(data.encode())
                src_file.seek(0)
                hashed_value = self.blob.get_file_hash(src_file.name)
                self.assertEqual(expected_hash, hashed_value)

    def test_create(self):

        for data, expected_compressed in self.data_to_compressed.items():
            expected_hash = self.data_to_hashed_name[data]
            with tempfile.NamedTemporaryFile() as src_file:
                src_file.write(data.encode())
                src_file.seek(0)
                with tempfile.TemporaryDirectory() as temp_dir:
                    actual_hash = self.blob.create(src_file.name, temp_dir)
                    blob_file = open(os.path.join(temp_dir, actual_hash), 'rb')
                    actual_compressed = blob_file.read()
                    self.assertEqual(gzip.decompress(actual_compressed), gzip.decompress(expected_compressed))
                    self.assertEqual(actual_hash, expected_hash)
                    blob_file.close()


class TreeTest(unittest.TestCase):

    def setUp(self):
        self.subdir_to_hash = {'.':'d25c3e80086290de5fb0c5ebc6c81ef0685870c3',
                       'subdir1':'d2b945ace691fe8522e868ebde016d0a53ac40ca',
                       'subdir2':'35d9d594f1d830505fb3132d8959e73119755114',
                       'subdir2/subdir3':'17aeddcc4d19a24eedc6024163cdb9b0fceb5faa'
                    }
        self.hash_to_data = {
            'd25c3e80086290de5fb0c5ebc6c81ef0685870c3': b'{"files": {"file1": "b75caba50711332063088fc53744f1c55b4445fe"}, '
            b'"subdirs": {"subdir1": "d2b945ace691fe8522e868ebde016d0a53ac40ca", "subdir2": "35d9d594f1d830505fb3132d8959e73119755114"}}',
            'd2b945ace691fe8522e868ebde016d0a53ac40ca': b'{"files": {"file2": "bfc385898eb83d5f15e84635a1ab1649cced4fcb"}, "subdirs": {}}',
            '35d9d594f1d830505fb3132d8959e73119755114': b'{"files": {"file3": "41cd77870f7d97e5b5a32b87a12343312ffbc065"}, "subdirs": '
            b'{"subdir3": "17aeddcc4d19a24eedc6024163cdb9b0fceb5faa"}}',
            '17aeddcc4d19a24eedc6024163cdb9b0fceb5faa': b'{"files": {"file4": "f0ef9dfd4b499f54cdcc15d0fc95204d92207790"}, "subdirs": {}}',

        }
        self.test_dir = tempfile.TemporaryDirectory()
        copy_tree('./test/test_dir/', self.test_dir.name)
        self.tree = objects.Tree(self.test_dir.name)
        self.tree.create()

    def tearDown(self):
        del self.test_dir

    def test_create(self):
        for _, hash_val in self.subdir_to_hash.items():
            subtree_path = os.path.join(self.tree.objects_path, hash_val)
            self.assertTrue(os.path.exists(subtree_path))

    def test_get_tree(self):
        for hash_val, expected_data in self.hash_to_data.items():
            tree_path = os.path.join(self.tree.objects_path, hash_val)
            tree_blob = open(tree_path, 'rb')
            actual_data = tree_blob.read()
            self.assertEqual(actual_data, expected_data)
            tree_blob.close()
