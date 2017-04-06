import argparse
import mock
import os
import tempfile
import unittest
import shutil
import re
import sys

from dogen.plugins.repo import Repo
from dogen.generator import Generator

class TestPackage(unittest.TestCase):
    def setUp(self):
        self.workdir = tempfile.mkdtemp(prefix='test_repo_plugin')
        self.descriptor = tempfile.NamedTemporaryFile(delete=False)
        self.target_dir = os.path.join(self.workdir, "target")
        self.log = mock.Mock()

    def teardown(self):
        shutil.rmtree(self.workdir)

    def write_config(self, config):
        with self.descriptor as f:
            f.write(config.encode())

    def prepare_dogen(self, repo_files_dir=None):
        args = argparse.Namespace(path=self.descriptor.name, output=self.target_dir, without_sources=None,
                                  template=None, scripts_path=None, additional_script=None,
                                  skip_ssl_verification=None, repo_files_dir=repo_files_dir)
        self.dogen = Generator(self.log, args, [Repo])

    def test_custom_repo_files_should_add_two(self):
        open(os.path.join(self.workdir, "fedora.repo"), 'a').close()
        open(os.path.join(self.workdir, "test.repo"), 'a').close()

        self.write_config("release: '1'\nversion: '1'\ncmd:\n - whoami\nfrom: scratch\nname: someimage\npackages:\n - wget")
        self.prepare_dogen(self.workdir)
        self.dogen.run()

        self.assertIsNotNone(self.dogen.cfg)
        self.assertIsNotNone(self.dogen.cfg.get('packages'))
        self.assertIsInstance(self.dogen.cfg.get('packages'), list)
        self.assertIn("wget", self.dogen.cfg.get('packages'))

        dockerfile = open(os.path.join(self.target_dir, "Dockerfile")).read()

        sys.stderr.write("\t\t\tDEBUGDEBUG\n{}\n".format(dockerfile))
        self.assertTrue(re.match(r'.*yum install[^\n]+wget', dockerfile, re.DOTALL))
        self.assertTrue(re.match(r'.*rpm -q +wget', dockerfile, re.DOTALL))
