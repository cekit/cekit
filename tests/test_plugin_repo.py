import argparse
import mock
import os
import tempfile
import unittest
import shutil

from dogen.plugins.repo import Repo
from dogen.generator import Generator

class MockDogen():
    def __init__(self, log, cfg={}):
        self.log = log
        self.descriptor = 0
        self.output = ""
        self.cfg = cfg

class TestRepoPlugin(unittest.TestCase):
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

    def test_should_skip_plugin_if_no_path_to_repo_is_provided(self):
        self.write_config("release: '1'\nversion: '1'\ncmd:\n - whoami\nfrom: scratch\nname: someimage\n")
        self.prepare_dogen()
        self.dogen.run()

        self.assertIsNotNone(self.dogen.cfg)
        self.assertIsNone(self.dogen.cfg.get('additional_repos'))
        self.log.debug.assert_any_call("No directory with YUM repo files specified, skipping repo plugin")

    def test_should_skip_plugin_if_path_to_repo_is_provided_but_there_are_no_packages_to_install(self):
        self.write_config("release: '1'\nversion: '1'\ncmd:\n - whoami\nfrom: scratch\nname: someimage\n")
        self.prepare_dogen("/path/to/repo")
        self.dogen.run()

        self.assertIsNotNone(self.dogen.cfg)
        self.assertIsNone(self.dogen.cfg.get('additional_repos'))
        self.log.debug.assert_any_call("There are no packages to install, no repository files will be added either")

    def test_custom_repo_files_should_fail_if_there_is_no_packages_section_and_path_to_repo_dir_is_provided(self):
        self.write_config("release: '1'\nversion: '1'\ncmd:\n - whoami\nfrom: scratch\nname: someimage\npackages:\n - wget")
        self.prepare_dogen("/path/to/repo")

        with self.assertRaises(Exception) as context:
            self.dogen.run()

        self.assertTrue("Provided path to directory with repo files: '/path/to/repo' does not exists or is not a directory" in str(context.exception))
        self.assertIsNotNone(self.dogen.cfg)
        self.assertIsNone(self.dogen.cfg.get('additional_repos'))

    def test_custom_repo_files_should_add_two(self):
        open(os.path.join(self.workdir, "fedora.repo"), 'a').close()
        open(os.path.join(self.workdir, "test.repo"), 'a').close()

        self.write_config("release: '1'\nversion: '1'\ncmd:\n - whoami\nfrom: scratch\nname: someimage\npackages:\n - wget")
        self.prepare_dogen(self.workdir)
        self.dogen.run()

        self.assertIsNotNone(self.dogen.cfg)
        self.assertIsNotNone(self.dogen.cfg.get('additional_repos'))
        self.assertTrue(os.path.exists(os.path.join(self.target_dir, "repos", "fedora.repo")))
        self.assertTrue(os.path.exists(os.path.join(self.target_dir, "repos", "test.repo")))

        dockerfile = open(os.path.join(self.target_dir, "Dockerfile")).read()

        self.assertTrue('--enablerepo=fedora' in dockerfile)
        self.assertTrue('--enablerepo=test' in dockerfile)


