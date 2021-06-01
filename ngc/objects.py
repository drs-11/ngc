import gzip
import hashlib
import json
import logging
import os
import shutil
import time

log = logging.getLogger(__name__)

class NgcObject:
    """
    A general class for objects of ngc.
    """
    # TODO: Have NgcObject class actually have some common functions for all other Ngc objects

    BUF_SIZE = 65536
    HASHING_FUNCTION = 'sha1'

    def __init__(self):
        pass

    def compress_obj(self, obj_path, dst):
        """ Compress the given object using gzip. """

        with open(obj_path, "rb") as f_in, gzip.open(dst, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out, self.BUF_SIZE)
        log.debug("%s compressed." % obj_path)

    def extract_obj(self, obj_path, dst):
        """ Uncompress the given object using gzip. """

        with gzip.open(dst, "rb") as f_in, open(obj_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out, self.BUF_SIZE)
        log.debug("%s uncompressed." % obj_path)

    def get_file_hash(self, file_path):
        """ Return a hash value of the contents of the given file. """

        hashf = hashlib.new(self.HASHING_FUNCTION)

        with open(file_path, "rb") as f_in:
            while True:
                data = f_in.read(self.BUF_SIZE)
                if not data:
                    break
                hashf.update(data)

        return hashf.hexdigest()


class Blob(NgcObject):
    """
    All the files in a repository will be converted to a blob(binary
    large object), in a compressed form.
    It has a simple format of: <HEADER><CONTENT>
    where HEADER is: "blob<SPACE><CONTENT.LENGTH><NULL_CHAR>"
    """

    def __init__(self):
        pass

    def create(self, file_path, obj_path):
        """ Create the blob file for the specified file. """

        # get the hash value of file as name for blob file
        compressed_filename = self.get_file_hash(file_path)
        blob_path = os.path.join(obj_path, compressed_filename)

        # create the header for the blob file and write it
        header = bytes(self._create_header(os.path.getsize(file_path)), 'ascii')

        # write compressed data to the blob file with the specified format
        with open(file_path, 'rb') as f_in:
            with gzip.open(blob_path, "wb") as f_out: # TODO: reverse file handler's name
                f_out.write(header)
                shutil.copyfileobj(f_in, f_out, self.BUF_SIZE)

        return compressed_filename

    def get_header(self, file_path):
        """ Get the header contents from the blob file. """
        # TODO: header has almost no info, enrich it

        temp = b''
        header = b''

        with gzip.open(file_path, "rb") as blob_obj:
            while b"\x00" not in temp:
                temp = blob_obj.read(1)
                if not temp:
                    break
                header += temp

        return header.decode()

    def get_content(self, file_path):
        """ Get contents of a blob file. """
        temp = b""
        header = b""

        with gzip.open(file_path, "rb") as f_in:
            while b"\x00" not in header:
                temp = f_in.read(1)
                if not temp:
                    break
                header += temp
            content = f_in.read()

        return content

    def extract_content(self, file_path, dst):
        """ Extract contents of a blob file to destination file. """
        header = b""

        with gzip.open(file_path, "rb") as f_in:
            with open(dst, "wb") as f_out:
                while b"\x00" not in header:
                    header = f_in.read(1)
                while True:
                    buf_data = f_in.read(self.BUF_SIZE)
                    if not buf_data:
                        break
                    f_out.write(buf_data)

    def get_file_hash(self, file_path):
        """ Overriden file hash function to include header value as well. """

        compressed_filename = None
        hashf = hashlib.new(self.HASHING_FUNCTION)
        header = self._create_header(os.path.getsize(file_path))

        hashf.update(bytes(header, 'ascii'))

        with open(file_path, "rb") as f_in:
            while True:

                data = f_in.read(self.BUF_SIZE)
                if not data:
                    break
                hashf.update(data)

        compressed_filename = hashf.hexdigest()
        return compressed_filename

    def _create_header(self, content_length):
        """ Create header with the format: 'blob<SPACE><CONTENT.LENGTH><NULL_CHAR>' """
        return f"blob {content_length}\x00"

class Tree(NgcObject):
    """
    Tree object will represent the structure of the repository. It will
    have a listing of files and other subdirectories.
    """

    FILES = 'files'
    SUBDIRS = 'subdirs'

    def __init__(self, path=None):
        if not path: path = os.getcwd()
        self.path = path
        self.objects_path = os.path.join(self.path, '.ngc/objects')
        # if not os.path.exists(self.objects_path): os.makedirs(self.objects_path)
        self.current_tree_hash = None
        self.blob = Blob()

    def create(self, path=None):
        if not path: path = self.path
        tree_obj = dict()
        files = dict()
        subdirs = dict()
        log.debug("generating tree object...")

        # traverse repository and generate blob files
        for item in os.listdir(path):
            log.debug("traversing: %s" % (path))
            # log.debug("item - %s" % (item))
            item_path = os.path.join(path, item)
            log.debug("item found: %s" % (item_path))

            if item.startswith("."):
                continue

            if os.path.isfile(item_path):
                # generate file's hash to use it as filename
                file_hash = self.blob.get_file_hash(item_path)

                # if item not already creates as blob, create it
                if not os.path.exists(os.path.join(self.objects_path, file_hash)):
                    file_hash = self.blob.create(item_path, self.objects_path)
                    log.debug("blob created for: %s" % (item))

                files[item] = file_hash

            elif os.path.isdir(item_path):

                # if item is a directory, recursively create another tree object
                subdir_hash = self.create(item_path)
                subdirs[item] = subdir_hash
                log.info("tree created for: %s" % (item))

            else:
                log.warning("Unknown file type found. Skipping.")

        # fill tree_obj with blob info
        tree_obj[self.FILES] = files
        tree_obj[self.SUBDIRS] = subdirs

        # convert dict to json stream
        tree_json = json.dumps(tree_obj)
        tree_json_bytes = tree_json.encode()

        # write tree obj to file
        hashf = hashlib.new(self.HASHING_FUNCTION)
        hashf.update(tree_json_bytes)
        hashed_value = hashf.hexdigest()
        tree_obj_path = os.path.join(self.objects_path, hashed_value)

        with open(tree_obj_path, 'wb') as tree_file:
            tree_file.write(tree_json_bytes)

        self.current_tree_hash = hashed_value # TODO: worst jugad ever, resolve testing for this

        return hashed_value

    def get_tree_dict(self, tree_hash):
        """ Get tree details from file as dict. """
        tree_file_path = os.path.join(self.objects_path, tree_hash)
        if not os.path.exists(tree_file_path):
            log.warning("Tree file doesn't exist.")
            return
        tree_dict = None

        with open(tree_file_path, "rb") as tree_file:
            tree_dict = json.load(tree_file)

        return tree_dict


class Commit(NgcObject):
    """
    Commit object will contain hash references and to its tree
    object and parent commit. It will also contain other info such
    as author and committer info.
    """

    TREE = 'tree'
    PARENT = "parent"
    AUTHOR = 'author'
    COMMITTER = 'committer'
    MSG = 'message'

    def __init__(self, path=None):
        if not path: path = os.getcwd()
        self.path = path
        self.objects_path = os.path.join(path, ".ngc/objects")
        # if not os.path.exists(self.objects_path): os.makedirs(self.objects_path)
        self.commit_dict = None

    def create(self, tree_hash, author_details, committer_details, message,
               parent_hash=None):
        """
        Create a commit object for a repository.
        TODO: reduce parameter values?

        :param tree_hash: Hash value of the root tree object.
        :param author_details: Details of author of the repo.
        TODO: refine author and committer detail structure
        :param committer_details: Details of the person who committed.
        :param message: Commit message.
        :param parent_hash: Hash value of parent commit/
        :type parent_hash: str
        :type message: str
        :type committer_details: dict
        :type author_details: dict
        :type tree_hash: str
        :returns: Hash value of tree file created.
        :rtype: str
        """
        commit_obj = dict()
        # TODO: forgot to use time_stamp
        time_stamp = time.time()

        # fill commit_obj with info
        commit_obj[self.TREE] = tree_hash
        commit_obj[self.AUTHOR] = author_details
        commit_obj[self.COMMITTER] = committer_details
        commit_obj[self.MSG] = message
        if parent_hash:
            commit_obj[self.PARENT] = parent_hash

        self.commit_dict = commit_obj

        # generate json stream
        commit_json = json.dumps(commit_obj)
        commit_json_bytes = commit_json.encode()

        # write commit_obj json to file
        hashf = hashlib.new(self.HASHING_FUNCTION)
        hashf.update(commit_json_bytes)
        hashed_value = hashf.hexdigest()
        commit_obj_path = os.path.join(self.objects_path, hashed_value)

        with open(commit_obj_path, 'wb') as tree_file:
            tree_file.write(commit_json_bytes)

        return hashed_value

    def print_commit_file(self, commit_hash):
        """ Print commit details from a commit file. """
        commit_path = os.path.join(self.objects_path, commit_hash)
        if not os.path.exists(commit_path):
            log.warning("Commit file doesn't exist.")
            return 
        commit_json = None

        with open(commit_path, 'rb') as commit_file:
            commit_json = json.load(commit_file)

        print("Commit:", commit_hash)
        # print(self.TREE, commit_json[self.TREE])
        if self.PARENT in commit_json: print(self.PARENT, commit_json[self.PARENT])
        print(self.AUTHOR, commit_json[self.AUTHOR])
        print(self.COMMITTER, commit_json[self.COMMITTER])
        print('\n' + commit_json[self.MSG] + '\n')

    def print_commit_dict(self):
        """ Print commit details from the class object. """
        if not self.commit_dict:
            log.warning('No commit object created.\n Create commit object first '
                            'to print commit details.')
            return

        print(self.TREE, self.commit_dict[self.TREE])
        if self.PARENT in self.commit_dict: print(self.PARENT, self.commit_dict[self.PARENT])
        print(self.AUTHOR, self.commit_dict[self.AUTHOR])
        print(self.COMMITTER, self.commit_dict[self.COMMITTER])
        print('\n' + self.commit_dict[self.MSG])
        
    def get_commit_dict_from_file(self, commit_hash):
        """ Get the commit details from a commit file. """
        commit_path = os.path.join(self.objects_path, commit_hash)
        commit_json = None

        with open(commit_path, 'rb') as commit_file:
            commit_json = json.load(commit_file)

        return commit_json

    def get_tree_hash(self, commit_hash):
        #TODO: why does this function exist?
        commit_path = os.path.join(self.objects_path, commit_hash)

        with open(commit_path, 'rb') as commit_file:
            commit_json = json.load(commit_file)

        return commit_json[self.TREE]
