import os
import subprocess

from six.moves import urllib

class Chdir(object):

    """ Context manager for changing the current working directory """

    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)

class Tools(object):
    @staticmethod
    def repo_info(path):

        with Chdir(path):
            name = os.path.basename(subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).strip())
            branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).strip()
            commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).strip()

        return name, branch, commit

    @staticmethod
    def decision(question):
        if raw_input("\n%s [Y/n] " % question) in ["", "y", "Y"]:
            return True

        return False

    @staticmethod
    def is_url(location):
        """ Checks if provided path is a URL """
        return bool(urllib.parse.urlparse(location).netloc)
