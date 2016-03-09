import unittest
import mock
import six
import tarfile
import os
import tempfile

from dogen.generator import Generator
from dogen.errors import Error
from dogen.version import version

class TestConfig(unittest.TestCase):
    def setUp(self):
        self.log = mock.Mock()
        self.descriptor = tempfile.NamedTemporaryFile(delete=False)

    def tearDown(self):
        os.remove(self.descriptor.name)

    def test_default_values(self):
        self.generator = Generator(self.log, self.descriptor.name, "target")
        self.assertEqual(self.generator.output, "target")
        self.assertEqual(self.generator.dockerfile, "target/Dockerfile")
        self.assertEqual(self.generator.descriptor, self.descriptor.name)
        self.assertEqual(self.generator.template, None)
        self.assertEqual(self.generator.scripts, None)
        self.assertEqual(self.generator.additional_scripts, None)
        self.assertEqual(self.generator.without_sources, False)
        self.assertEqual(self.generator.dist_git, False)
        # Set to True in the configure() method later 
        self.assertEqual(self.generator.ssl_verify, None)
        self.assertFalse(self.generator.dist_git)

    def test_fail_if_version_mismatch(self):
        with self.descriptor as f:
            f.write("dogen:\n  version: 99999.9.9-dev1".encode())

        self.generator = Generator(self.log, self.descriptor.name, "target")

        with self.assertRaises(Error) as cm:
            self.generator.configure()

        self.assertEquals(
            str(cm.exception), "You try to parse descriptor that requires Dogen version 99999.9.9-dev1, but you run version %s" % version)

    def test_skip_ssl_verification_in_descriptor(self):
        with self.descriptor as f:
            f.write("dogen:\n  ssl_verify: false".encode())

        generator = Generator(self.log, self.descriptor.name, "target")
        generator.configure()
        self.assertFalse(generator.ssl_verify)

    def test_do_not_skip_ssl_verification_in_descriptor(self):
        with self.descriptor as f:
            f.write("dogen:\n  ssl_verify: true".encode())

        generator = Generator(self.log, self.descriptor.name, "target")
        generator.configure()
        self.assertTrue(generator.ssl_verify)

    def test_custom_template_in_descriptor(self):
        with self.descriptor as f:
            f.write("dogen:\n  template: custom-template.jinja".encode())

        generator = Generator(self.log, self.descriptor.name, "target")
        generator.configure()
        self.assertEqual(generator.template, "custom-template.jinja")

    def test_custom_template_in_cli_should_override_in_descriptor(self):
        with self.descriptor as f:
            f.write("dogen:\n  template: custom-template.jinja".encode())

        generator = Generator(self.log, self.descriptor.name, "target", template="cli-template.jinja")
        generator.configure()
        self.assertEqual(generator.template, "cli-template.jinja")

    def test_do_not_skip_ssl_verification_in_cli_true_should_override_descriptor(self):
        with self.descriptor as f:
            f.write("dogen:\n  ssl_verify: false".encode())

        generator = Generator(self.log, self.descriptor.name, "target", ssl_verify=True)
        generator.configure()
        self.assertTrue(generator.ssl_verify)

    def test_do_not_skip_ssl_verification_in_cli_false_should_override_descriptor(self):
        with self.descriptor as f:
            f.write("dogen:\n  ssl_verify: true".encode())

        generator = Generator(self.log, self.descriptor.name, "target", ssl_verify=False)
        generator.configure()
        self.assertFalse(generator.ssl_verify)

    @mock.patch('dogen.generator.os.path.exists', return_value=True)
    def test_custom_scripts_dir_in_descriptor(self, mock_patch):
        with self.descriptor as f:
            f.write("dogen:\n  scripts: custom-scripts".encode())

        generator = Generator(self.log, self.descriptor.name, "target")
        generator.configure()
        mock_patch.assert_called_with('custom-scripts')
        self.assertEqual(generator.scripts, "custom-scripts")

    @mock.patch('dogen.generator.os.path.exists', return_value=True)
    def test_custom_scripts_dir_in_cli_should_override_in_descriptor(self, mock_patch):
        with self.descriptor as f:
            f.write("dogen:\n  template: custom-scripts".encode())

        generator = Generator(self.log, self.descriptor.name, "target", scripts="custom-scripts-cli")
        generator.configure()
        mock_patch.assert_called_with('custom-scripts-cli')
        self.assertEqual(generator.scripts, "custom-scripts-cli")

    @mock.patch('dogen.generator.os.path.exists', return_value=True)
    def test_scripts_dir_found_by_convention(self, mock_patch):
        with self.descriptor as f:
            f.write("dogen:\n  scripts: custom-scripts".encode())

        generator = Generator(self.log, self.descriptor.name, "target")
        generator.configure()
        mock_patch.assert_called_with('custom-scripts')
        self.assertEqual(generator.scripts, "custom-scripts")

    def test_custom_additional_scripts_in_descriptor(self):
        with self.descriptor as f:
            f.write("dogen:\n  additional_scripts:\n    - http://host/somescript".encode())

        generator = Generator(self.log, self.descriptor.name, "target")
        generator.configure()
        self.assertEqual(generator.additional_scripts, ["http://host/somescript"])

    def test_custom_additional_scripts_in_cli_should_override_in_descriptor(self):
        with self.descriptor as f:
            f.write("dogen:\n  additional_scripts:\n    - http://host/somescript".encode())

        generator = Generator(self.log, self.descriptor.name, "target", additional_scripts=["https://otherhost/otherscript"])
        generator.configure()
        self.assertEqual(generator.additional_scripts, ["https://otherhost/otherscript"])
