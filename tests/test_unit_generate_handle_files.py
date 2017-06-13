import argparse
import unittest
import mock
import os
import six

from dogen.generator import Generator
from dogen.errors import Error
from dogen.tools import Tools

class TestURL(unittest.TestCase):
    def setUp(self):
        self.log = mock.Mock()
        args = argparse.Namespace(path="image.yaml", output="target", without_sources=None,
                                  template=None, scripts_path=None, additional_script=None,
                                  skip_ssl_verification=None)
        self.generator = Generator(self.log, args)

    def test_local_file(self):
        self.assertFalse(Tools.is_url("a_file.tmp"))

    def test_remote_http_file(self):
        self.assertTrue(Tools.is_url("http://host/file.tmp"))

    def test_remote_https_file(self):
        self.assertTrue(Tools.is_url("https://host/file.tmp"))

class TestFetchFile(unittest.TestCase):
    def setUp(self):
        self.log = mock.Mock()
        args = argparse.Namespace(path="image.yaml", output="target", without_sources=None,
                                  template=None, scripts_path=None, additional_script=None,
                                  skip_ssl_verification=None)
        self.generator = Generator(self.log, args)

    @mock.patch('dogen.generator.requests.get')
    def test_fetching_with_filename(self, mock_requests):
        def iter_content(**args):
            return ["file-content"]

        mock_requests.return_value.status_code = 200
        mock_requests.return_value.iter_content = iter_content

        with mock.patch.object(six.moves.builtins, 'open', mock.mock_open()) as mock_file:
            self.assertEqual(self.generator._fetch_file("https://host/file.tmp", "some-file"), "some-file")
            mock_requests.assert_called_with('https://host/file.tmp', verify=None, stream=True)
            mock_file().write.assert_called_once_with("file-content")

        self.log.debug.assert_any_call("Fetching 'https://host/file.tmp' file...")
        self.log.debug.assert_any_call("Fetched file will be saved as 'some-file'...")


    @mock.patch('dogen.generator.tempfile.mktemp', return_value="tmpfile")
    @mock.patch('dogen.generator.requests.get')
    def test_fetching_with_tmpfile(self, mock_requests, mock_tempfile):
        def iter_content(**args):
            return ["file-content"]

        mock_requests.return_value.status_code = 200
        mock_requests.return_value.iter_content = iter_content

        with mock.patch.object(six.moves.builtins, 'open', mock.mock_open()) as mock_file:
            self.assertEqual(self.generator._fetch_file("https://host/file.tmp"), "tmpfile")
            mock_tempfile.assert_called_with("-dogen")
            mock_requests.assert_called_with('https://host/file.tmp', verify=None, stream=True)
            mock_file().write.assert_called_once_with("file-content")

        self.log.debug.assert_any_call("Fetching 'https://host/file.tmp' file...")
        self.log.debug.assert_any_call("Fetched file will be saved as 'tmpfile'...")

class TestCustomTemplateHandling(unittest.TestCase):
    def setUp(self):
        self.log = mock.Mock()
        args = argparse.Namespace(path="image.yaml", output="target", without_sources=None,
                                  template="http://host/custom-template", scripts_path=None,
                                  additional_script=None, skip_ssl_verification=None)
        self.generator = Generator(self.log, args)

    def test_do_not_fail_if_no_template_is_provided(self):
        args = argparse.Namespace(path="image.yaml", output="target", without_sources=None,
                                  template=None, scripts_path=None, additional_script=None,
                                  skip_ssl_verification=None)
        self.generator = Generator(self.log, args)

        fetch_file_mock = mock.Mock()
        self.generator._fetch_file = fetch_file_mock

        self.assertEqual(self.generator.template, None)
        self.generator._handle_custom_template()
        fetch_file_mock.assert_not_called()
        self.assertEqual(self.generator.template, None)

    @mock.patch('dogen.generator.os.path.exists', return_value=True)
    def test_fetch_template_success(self, mock_path):
        fetch_file_mock = mock.Mock(return_value="some-tmp-file")
        self.generator._fetch_file = fetch_file_mock

        self.assertEqual(self.generator.template, "http://host/custom-template")
        self.generator._handle_custom_template()
        fetch_file_mock.assert_called_with("http://host/custom-template")
        self.assertEqual(self.generator.template, "some-tmp-file")

    @mock.patch('dogen.generator.os.path.exists', return_value=False)
    def test_fetch_template_with_error(self, mock_path):
        fetch_file_mock = mock.Mock(return_value="some-tmp-file")
        self.generator._fetch_file = fetch_file_mock

        self.assertEqual(self.generator.template, "http://host/custom-template")

        with self.assertRaises(Error) as cm:
            self.generator._handle_custom_template()

        self.assertEquals(str(cm.exception), "Template file 'some-tmp-file' could not be found. Please make sure you specified correct path or check if the file was successfully fetched.")

        fetch_file_mock.assert_called_with("http://host/custom-template")
        self.assertEqual(self.generator.template, "some-tmp-file")

class TestHandleSources(unittest.TestCase):
    def setUp(self):
        self.log = mock.Mock()
        args = argparse.Namespace(path="image.yaml", output="target", without_sources=None,
                                  template="http://host/custom-template", scripts_path=None,
                                  additional_script=None, skip_ssl_verification=None)
        self.generator = Generator(self.log, args)

    def test_fetch_artifact_without_url_should_fail(self):
        self.generator.cfg = {'sources': [{'artifact': 'jboss-eap.zip'}]}

        with self.assertRaises(Error) as cm:
            self.generator.handle_sources()

        self.assertEquals(str(cm.exception), "Artifact 'jboss-eap.zip' could not be fetched!")

    @mock.patch('dogen.generator.Generator._fetch_file', side_effect=Error("Blah"))
    def test_fetch_artifact_should_fail_when_fetching_fails(self, mock_fetch_file):
        self.generator.cfg = {'sources': [{'artifact': 'http://jboss-eap.zip'}]}

        with self.assertRaises(Error) as cm:
            self.generator.handle_sources()

        self.assertEquals(str(cm.exception), "Could not download artifact from orignal location, reason: Blah")

    @mock.patch('dogen.generator.Generator._fetch_file', side_effect=[Error("cached"), Error("original")])
    def test_fetch_artifact_should_fail_when_cached_download_failed_and_original_failed_too(self, mock_fetch_file):
        self.generator.cfg = {'sources': [{'artifact': 'http://host.com/jboss-eap.zip'}]}

        k = mock.patch.dict(os.environ, {'DOGEN_SOURCES_CACHE':'http://cache/get?#algorithm#=#hash#'})
        k.start()

        with self.assertRaises(Error) as cm:
            self.generator.handle_sources()

        k.stop()

        self.assertEquals(str(cm.exception), "Could not download artifact from orignal location, reason: original")
        mock_fetch_file.assert_has_calls([mock.call('http://cache/get?#algorithm#=#hash#', 'target/jboss-eap.zip'), mock.call('http://host.com/jboss-eap.zip', 'target/jboss-eap.zip')])

    @mock.patch('dogen.generator.Generator._fetch_file')
    def test_fetch_artifact_should_fail_with_nice_message_when_artifact_without_url_is_not_found_locally(self, mock_fetch_file):
        self.generator.cfg = {'sources': [{'artifact': 'jboss-eap.zip'}]}

        with self.assertRaises(Error) as cm:
            self.generator.handle_sources()

        self.assertEquals(str(cm.exception), "Artifact 'jboss-eap.zip' could not be fetched!")
        mock_fetch_file.assert_not_called()
        self.log.info.assert_any_call("Please download the 'jboss-eap.zip' artifact manually and save it as 'target/jboss-eap.zip'")

    @mock.patch('dogen.generator.Generator._fetch_file')
    def test_fetch_artifact_should_fetch_file_from_cache(self, mock_fetch_file):
        self.generator.cfg = {'sources': [{'artifact': 'http://host.com/jboss-eap.zip'}]}

        k = mock.patch.dict(os.environ, {'DOGEN_SOURCES_CACHE':'http://cache/get?#filename#'})
        k.start()
        self.generator.handle_sources()
        k.stop()

        # No checksum provided and computed
        self.assertEquals(self.generator.cfg['artifacts'], {'jboss-eap.zip': None})
        mock_fetch_file.assert_called_with('http://cache/get?jboss-eap.zip', 'target/jboss-eap.zip')

    @mock.patch('dogen.generator.Generator._fetch_file')
    @mock.patch('dogen.generator.os.path.exists', return_value=False)
    def test_fetch_artifact_should_fetch_file(self, mock_path_exists, mock_fetch_file):
        self.generator.cfg = {'sources': [{'artifact': 'http://host.com/jboss-eap.zip'}]}
        self.generator.handle_sources()
        # No checksum provided and computed
        self.assertEquals(self.generator.cfg['artifacts'], {'jboss-eap.zip': None})
        mock_fetch_file.assert_called_with('http://host.com/jboss-eap.zip', 'target/jboss-eap.zip')

    @mock.patch('dogen.generator.Generator._fetch_file', side_effect=[Error("cached"), None])
    def test_fetch_artifact_should_download_from_original_location_if_cached_location_failed(self, mock_fetch_file):
        self.generator.cfg = {'sources': [{'artifact': 'http://host.com/jboss-eap.zip'}]}

        k = mock.patch.dict(os.environ, {'DOGEN_SOURCES_CACHE':'http://cache/get?#algorithm#=#hash#'})
        k.start()
        self.generator.handle_sources()
        k.stop()

        self.assertEquals(self.generator.cfg['artifacts'], {'jboss-eap.zip': None})
        mock_fetch_file.assert_has_calls([mock.call('http://cache/get?#algorithm#=#hash#', 'target/jboss-eap.zip'), mock.call('http://host.com/jboss-eap.zip', 'target/jboss-eap.zip')])

    @mock.patch('dogen.generator.Generator._fetch_file')
    @mock.patch('dogen.generator.os.path.exists', return_value=True)
    def test_fetch_artifact_should_not_fetch_file_if_exists(self, mock_path_exists, mock_fetch_file):
        self.generator.cfg = {'sources': [{'artifact': 'http://host.com/jboss-eap.zip'}]}
        self.generator.handle_sources()
        # No checksum provided and computed
        self.assertEquals(self.generator.cfg['artifacts'], {'jboss-eap.zip': None})
        mock_fetch_file.assert_not_called()
