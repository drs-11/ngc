import json
import logging
import os
import time
from pathlib import Path

from . import objects

log = logging.getLogger(__name__)

class Command:
    """
    Main class dealing with ngc commands.
    """

    USER_NAME = 'user_name'
    USER_EMAIL = 'user_email'
    TIMESTAMP = 'timestamp'

    def __init__(self, repo_path=None):
        if not repo_path: repo_path=os.getcwd()
        self.repo_path = repo_path
        self.user_details = self._get_user_details()
        self.author_details = self._get_author_details()
        self.head = self._get_current_commit_hash()
        self.obj_blob = objects.Blob()
        self.obj_tree = objects.Tree(self.repo_path)
        self.obj_commit = objects.Commit(self.repo_path)

    def init(self):
        """
        Create required subdirectories to help maintain repository status and history.
        """

        # check if user has been configured
        if not self.user_details.get(self.USER_NAME):
            print("Please configure user settings through config command first!")
            return

        self.author_details = self.user_details
        self.author_details[self.TIMESTAMP] = time.time()
        self._set_author_details()
        ngc_path = os.path.join(self.repo_path, ".ngc")
        objects_path = os.path.join(ngc_path, "objects")

        if not os.path.exists(ngc_path): os.makedirs(ngc_path)
        if not os.path.exists(objects_path): os.makedirs(objects_path)

    def status(self):
        """
        Display the status of the repository in regards of file changes.
        """
        modified_files = list()
        def print_mod(file_path, blob_path):
            file_name = file_path.split("/")[-1]
            print(f"modified:    {file_name}")
        def print_del(file_path, blob_path):
            file_name = file_path.split("/")[-1]
            print(f"deleted:    {file_name}")
        def print_add(file_path):
            file_name = file_path.split("/")[-1]
            print(f"added:    {file_name}")


        print(f"On branch {self.head}")
        print("Changes not committed:")
        self._check_modified_files(mod_list=modified_files, mod_func=print_mod, del_func=print_del)
        self._check_added_files(mod_list=modified_files, add_func=print_add)
        print('Use "ngc commit" to add changes to a new commit')

    def diff(self):
        pass

    def commit(self, message):
        """
        Commit changes of a repository.
        Note: Staging and unstaging not supported right now
        """
        # generate the tree for the repository and convert files
        # to blobs
        prev_tree_hash = self.obj_tree.current_tree_hash
        tree_hash = self.obj_tree.create()

        # if there are no changes, return
        if prev_tree_hash == self.obj_tree.current_tree_hash:
            print("No changes detected, nothing to commit.")
            return

        # get previous commit's hash if it exists
        parent_hash = self._get_current_commit_hash()

        # put the timestamp into commit
        self.user_details[self.TIMESTAMP] = time.time()

        # generate the commit object
        commit_hash = self.obj_commit.create(tree_hash, self.author_details,
                                             self.user_details, message, parent_hash)

        self._update_commit_hash(commit_hash)

    def reset(self):
        modified_files = list()
        def restore_file(file_path, blob_path):
            self.obj_blob.extract_content(dst=file_path, file_path=blob_path)
        def delete_file(file_path):
            os.remove(file_path)

        self._check_modified_files(mod_list=modified_files, mod_func=restore_file, del_func=restore_file)
        self._check_added_files(mod_list=modified_files, add_func=delete_file)

    def log(self, commit_hash=None):
        if commit_hash is None: commit_hash = self.head
        log.info("logging...")

        with open(os.path.join(self.repo_path, '.ngc/HEAD'), 'rb') as head_file:
            current_hash = head_file.read().decode()
            log.debug("current_hash variable: %s" % (current_hash))
            log.debug("commit_hash_hash variable: %s" % (commit_hash))
            log.debug("self.head variable: %s" % (self.head))

        while True:
            if current_hash == commit_hash:
                break
            else:
                with open(os.path.join(self.repo_path, f'.ngc/objects/{current_hash}'), 'rb') as commit_file:
                    commit_data = json.load(commit_file)
                current_hash = commit_data[self.obj_commit.PARENT]

        while True:
            self.obj_commit.print_commit_file(current_hash)
            with open(os.path.join(self.repo_path, f'.ngc/objects/{current_hash}'), 'rb') as commit_file:
                commit_data = json.load(commit_file)
            if self.obj_commit.PARENT not in commit_data: break
            else: current_hash = commit_data[self.obj_commit.PARENT]


    def checkout(self, commit_hash=None):
        if commit_hash is None: commit_hash = self.head

        for dirpath, dirnames, filenames in os.walk(self.repo_path):
            if ".ngc" in dirpath:
                continue
            for file in filenames:
                if file == ".authorinfo" : continue
                os.remove(os.path.join(dirpath, file))

        tree_hash = self.obj_commit.get_tree_hash(commit_hash)
        self._restore_files(tree_hash, self.repo_path)

    def config_user(self, user_name, user_email):
        """ Configure user details for ngc to use. """
        self.user_details[self.USER_NAME] = user_name
        self.user_details[self.USER_EMAIL] = user_email

        with open(os.path.join(str(Path.home()), ".userinfo"), 'w') as user_info_file:
            json.dump(self.user_details, user_info_file)

    def _get_user_details(self):
        """ Get user details from the config file(.userinfo) """
        # config file is stored in user's home directory
        info_file_path = os.path.join(str(Path.home()), ".userinfo")
        user_details = {self.USER_NAME : None,
                        self.USER_EMAIL : None,
                        self.TIMESTAMP : None}  # TODO: is timestamp as a key required here?

        if os.path.exists(info_file_path):
            with open(info_file_path, "r") as user_info_file:
                user_details = json.load(user_info_file)

        return user_details

    def _set_author_details(self):
        """ Set the current author info into local repository. """
        with open(os.path.join(self.repo_path, '.authorinfo'), 'w') as author_info_file:
            json.dump(self.author_details, author_info_file)

    def _get_author_details(self):
        """
        Get author info from current repo if it exists otherwise initialize empty info.
        """
        author_details = {self.USER_NAME : None,
                          self.USER_EMAIL : None,
                          self.TIMESTAMP : None}

        author_file_path = os.path.join(self.repo_path, '.authorinfo')
        if os.path.exists(author_file_path):
            with open(author_file_path, 'r') as author_info_file:
                author_details = json.load(author_info_file)

        return author_details

    def _get_current_commit_hash(self):
        """
        Retrieve current commit's hash from file HEAD if it exists.
        """
        commit_hash = None
        try:
            with open(os.path.join(self.repo_path, ".ngc/HEAD"), "r") as head_file:
                commit_hash = head_file.read()
        except FileNotFoundError:
            log.debug("No HEAD file found. Assuming there were no prior commits.")
        return commit_hash

    def _restore_files(self, tree_hash, dir_path):
        tree_dict = self.obj_tree.get_tree_dict(tree_hash)

        for file in tree_dict[self.obj_tree.FILES]:
            blob_name = tree_dict[self.obj_tree.FILES][file]
            blob_path = os.path.join(self.repo_path, ".ngc/objects", blob_name)
            file_path = os.path.join(dir_path, file)
            self.obj_blob.extract_content(blob_path, file_path)

        for subdir in tree_dict[self.obj_tree.SUBDIRS]:
            subdir_path = os.path.join(dir_path, subdir)
            subdir_hash = tree_dict[self.obj_tree.SUBDIRS][subdir]
            self._restore_files(subdir_hash, subdir_path)

    def _update_commit_hash(self, new_commit_hash):
        """
        Update commit hash wherever relevant.
        """
        self.head = new_commit_hash

        with open(os.path.join(self.repo_path, ".ngc/HEAD"), "w") as head_file:
            head_file.write(new_commit_hash)

        log.debug("Updated HEAD to %s" % (self.head))

    def _check_modified_files(self, tree=None, path=None, mod_list=None, mod_func=None, del_func=None):
        if path is None : path = self.repo_path
        if tree is None : tree = self.head

        if tree is self.head:
            with open(os.path.join(self.repo_path, ".ngc/objects", tree), "rb") as commit_file:
                commit_data = json.load(commit_file)
            tree = commit_data[self.obj_commit.TREE]
        with open(os.path.join(self.repo_path, ".ngc/objects", tree), "rb") as tree_file:
            tree_json = json.load(tree_file)
        for file in tree_json[self.obj_tree.FILES]:
            file_path = os.path.join(path, file)
            blob_path = os.path.join(self.repo_path, ".ngc/objects", tree_json[self.obj_tree.FILES][file])
            if os.path.exists(file_path):
                file_content = open(file_path, 'rb').read()
                blob_content = self.obj_blob.get_content(blob_path)
                if file_content != blob_content:
                    if type(mod_list) is list:
                        mod_list.append(file)
                    try:
                        mod_func(file_path, blob_path)
                    except TypeError:
                        pass
            else:
                try:
                    del_func(file_path, blob_path)
                except TypeError:
                    pass
        for subdir in tree_json[self.obj_tree.SUBDIRS]:
            new_path = os.path.join(path, subdir)
            new_tree = tree_json[self.obj_tree.SUBDIRS][subdir]
            self._check_modified_files(tree=new_tree, path=new_path, mod_list=mod_list, mod_func=mod_func, del_func=del_func)

    def _check_added_files(self, mod_list=None, add_func=None):

        for dirpath, dirnames, filenames in os.walk(self.repo_path):
            if "." in dirpath:
                continue
            for file in filenames:
                if file.startswith("."):
                    continue
                file_path = os.path.join(dirpath, file)
                hexdigest = self.obj_blob.get_file_hash(file_path)
                if hexdigest not in os.listdir(os.path.join(self.repo_path, '.ngc/objects')):
                    if type(mod_list) is list:
                        if file in mod_list:
                            continue
                    try:
                        add_func(file_path)
                    except TypeError:
                        pass
