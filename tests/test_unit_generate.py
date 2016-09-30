import argparse
import unittest
import mock
import tempfile
import os

from dogen.generator import Generator

class TestGenerateCustomRepoFiles(unittest.TestCase):

    # keys that must be present in config file but we don't care about
    # for specific tests
    basic_config ="release: '1'\nversion: '1'\ncmd:\n - whoami\nfrom: scratch\nname: someimage\n"

    def setUp(self):
        self.log = mock.Mock()
        self.descriptor = tempfile.NamedTemporaryFile(delete=False)

        with self.descriptor as f:
            f.write(self.basic_config.encode())
            f.write("dogen:\n  ssl_verify: true".encode())

        args = argparse.Namespace(path=self.descriptor.name, output="target", without_sources=None,
                                  template=None, scripts_path=None, additional_script=None,
                                  skip_ssl_verification=None)
        self.generator = Generator(self.log, args)
        self.generator.configure()

    def tearDown(self):
        os.remove(self.descriptor.name)

    def test_custom_repo_files_should_not_fail(self):
        with mock.patch('glob.glob') as mock_glob:
            mock_glob.return_value = []
            self.generator._handle_custom_repo_files()

        self.assertEqual(self.generator.cfg['additional_repos'], [])

    def test_custom_repo_files_should_add_two(self):
        with mock.patch('glob.glob') as mock_glob:
            mock_glob.return_value = ["scripts/jboss.repo", "scripts/other.repo"]
            self.generator._handle_custom_repo_files()

        self.assertIsNotNone(self.generator.cfg['additional_repos'])
        self.assertEqual(self.generator.cfg['additional_repos'], ['jboss', 'other'])
