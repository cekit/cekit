import argparse
import tempfile
import unittest
import mock
import os
import re
import shutil

from dogen.generator import Generator

# Generate a Dockerfile, and check what is in it.

class TestUser(unittest.TestCase):

    # keys that must be present in config file but we don't care about
    # for specific tests
    basic_config ="release: '1'\nversion: '1'\ncmd:\n - whoami\nfrom: scratch\nname: someimage\n"

    @classmethod
    def setUpClass(cls):
        cls.log = mock.Mock()
        cls.workdir = tempfile.mkdtemp(prefix="test_user")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.workdir)

    def setUp(self):
        self.yaml = os.path.join(self.workdir, "image.yaml")
        self.target = os.path.join(self.workdir, "target")
        os.mkdir(self.target)
        self.args = argparse.Namespace(path=self.yaml, output=self.target, without_sources=None,
                                       template=None, scripts_path=None, additional_script=None,
                                       skip_ssl_verification=None)
        with open(self.yaml, 'wb') as f:
            f.write(self.basic_config.encode())

    def tearDown(self):
        shutil.rmtree(self.target)

    def test_set_cmd_user(self):
        """
        Ensure that setting a user in the YAML generates a corresponding
        USER instruction in the Dockerfile, immediately before the CMD.
        """

        with open(self.yaml, 'ab') as f:
            f.write("user: 1347".encode())

        generator = Generator(self.log, self.args)
        generator.configure()
        generator.render_from_template()

        self.assertEqual(generator.cfg['user'], 1347)

        with open(os.path.join(self.target, "Dockerfile"), "r") as f:
            dockerfile = f.read()
            regex = re.compile(r'.*USER 1347\nCMD.*',  re.MULTILINE)
            self.assertRegexpMatches(dockerfile, regex)

    def test_default_cmd_user(self):
        """
        Ensure that not setting a user in the YAML generates a USER
        instruction in the Dockerfile, immediately before the CMD,
        defaulting to uid 0.
        """
        generator = Generator(self.log, self.args)
        generator.configure()
        generator.render_from_template()

        self.assertEqual(generator.cfg['user'], 0)

        with open(os.path.join(self.target, "Dockerfile"), "r") as f:
            dockerfile = f.read()
            regex = re.compile(r'.*USER 0\nCMD.*',  re.MULTILINE)
            self.assertRegexpMatches(dockerfile, regex)
