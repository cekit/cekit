import unittest
import mock
import tempfile
import os

from dogen.generator import Generator

class TestGenerateCustomRepoFiles(unittest.TestCase):
    def setUp(self):
        self.log = mock.Mock()
        self.descriptor = tempfile.NamedTemporaryFile(delete=False)

        with self.descriptor as f:
            f.write("dogen:\n  ssl_verify: true".encode())

        self.generator = Generator(self.log, self.descriptor.name, "target")
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
