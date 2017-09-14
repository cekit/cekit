import mock
import os
import requests
import tempfile
import unittest
import yaml

from concreate import descriptor
from concreate import tools
from concreate.errors import ConcreateError


class TestDescriptor(unittest.TestCase):

    def test_descriptor_schema_version(self):
        img_descriptor = descriptor.Descriptor.__new__(descriptor.Descriptor)
        img_descriptor.descriptor = {'schema_version': 1}
        img_descriptor.check_schema_version()

    def test_descriptor_schema_version_bad_version(self):
        img_descriptor = descriptor.Descriptor.__new__(descriptor.Descriptor)
        img_descriptor.descriptor = {'schema_version': 123}
        with self.assertRaises(ConcreateError):
            img_descriptor.check_schema_version()


class TestLabels(unittest.TestCase):

    def setUp(self):
        _, self.descriptor = tempfile.mkstemp()

    def tearDown(self):
        os.remove(self.descriptor)

    def prepare_descriptor(self, data={}):
        image = {'name': 'image/name', 'version': 1.0,
                 'from': 'from/image', 'schema_version': 1}
        image.update(data)

        with open(self.descriptor, 'w') as outfile:
            yaml.dump(image, outfile, default_flow_style=False)

    def test_no_labels_should_be_added(self):
        self.prepare_descriptor()

        img_descriptor = descriptor.Descriptor(self.descriptor, 'image')
        img_descriptor._process_labels()

        self.assertIsNone(img_descriptor.label('description'))
        self.assertIsNone(img_descriptor.label('summary'))
        self.assertIsNone(img_descriptor.label('maintainer'))

    def test_description_label_should_be_added(self):
        self.prepare_descriptor({'description': 'This is image description'})

        img_descriptor = descriptor.Descriptor(self.descriptor, 'image')
        img_descriptor._process_labels()

        self.assertIsNone(img_descriptor.label('maintainer'))
        self.assertEqual(img_descriptor.label('description').get(
            'value'), 'This is image description')
        # In this case the 'summary' label should be also set
        self.assertEqual(img_descriptor.label('summary').get(
            'value'), 'This is image description')

    def test_description_and_summary_labels_should_not_be_overriden(self):
        self.prepare_descriptor({'description': 'This is image description', 'labels': [
                                {'name': 'summary', 'value': 'summary value'},
                                {'name': 'description', 'value': 'description value'}]})

        img_descriptor = descriptor.Descriptor(self.descriptor, 'image')
        img_descriptor._process_labels()

        self.assertIsNone(img_descriptor.label('maintainer'))
        self.assertEqual(img_descriptor.label(
            'description').get('value'), 'description value')
        self.assertEqual(img_descriptor.label(
            'summary').get('value'), 'summary value')


@mock.patch('subprocess.check_output')
class TestGitResource(unittest.TestCase):

    def test_repository_dir_is_constructed_properly(self, mock):
        resource = descriptor.GitResource(
            {'git': {'url': 'url/repo', 'ref': 'ref'}})
        self.assertEqual(resource.copy('dir'), 'dir/repo-ref')

    def test_git_clone(self, mock):
        resource = descriptor.GitResource(
            {'git': {'url': 'url', 'ref': 'ref'}})
        resource.copy('dir')
        mock.assert_called_with(['git',
                                 'clone',
                                 '--depth',
                                 '1',
                                 'url',
                                 'dir/url-ref',
                                 '-b',
                                 'ref'],
                                stderr=-2)


class TestUrlResource(unittest.TestCase):
    res = requests.Response()
    res.status_code = 200
    res.iter_content = lambda chunk_size: [b'test']

    res_bad_status = requests.Response()
    res_bad_status.status_code = 500

    def setUp(self):
        tools.cfg = {}

    @mock.patch('requests.get', return_value=res)
    def test_fetching_disable_ssl_verify(self, mock):
        tools.cfg['common'] = {}
        tools.cfg['common']['ssl_verify'] = "False"
        resource = descriptor.UrlResource(
            {'name': 'file', 'url': 'https:///dummy'})
        try:
            resource.copy()
        except:
            pass
        mock.assert_called_with('https:///dummy', stream=True, verify=False)
        tools.cfg['common']['ssl_verify'] = "True"
        os.remove('file')
        tools.cfg = {}

    @mock.patch('requests.get', return_value=res_bad_status)
    def test_fetching_bad_status_code(self, mock):
        resource = descriptor.UrlResource(
            {'name': 'file', 'url': 'http:///dummy'})
        with self.assertRaises(ConcreateError):
            resource.copy()

    @mock.patch('requests.get', return_value=res)
    def test_fetching_file_exists_but_used_as_is(self, mock):
        """
        It should not download the file, because we didn't
        specify any hash algorithm, so integrity checking is
        implicitly disabled here.
        """
        with open('file', 'w') as f:  # noqa: F841
            pass
        resource = descriptor.UrlResource(
            {'name': 'file', 'url': 'http:///dummy'})
        resource.copy()
        mock.assert_not_called()
        os.remove('file')

    @mock.patch('requests.get', return_value=res)
    def test_fetching_file_exists_fetched_again(self, mock):
        """
        It should download the file again, because available
        file locally doesn't match checksum.
        """
        with open('file', 'w') as f:  # noqa: F841
            pass
        resource = descriptor.UrlResource(
            {'name': 'file', 'url': 'http:///dummy', 'md5': '123456'})
        with self.assertRaises(ConcreateError):
            # Checksum will fail, because the "downloaded" file
            # will not have md5 equal to 123456. We need investigate
            # mocking of requests get calls to do it properly
            resource.copy()
        mock.assert_called_with('http:///dummy', verify=True, stream=True)
        os.remove('file')

    def test_resource_verify_disabled_integrity_check(self):
        descriptor.Resource.check_integrity = False
        resource = descriptor.Resource.__new__(descriptor.Resource)
        resource.checksums = {}
        self.assertTrue(resource._Resource__verify('dummy'))
        descriptor.Resource.check_integrity = True

    @mock.patch('concreate.descriptor.Resource._Resource__check_sum')
    def test_resource_verify(self, mock):
        resource = descriptor.Resource.__new__(descriptor.Resource)
        resource.checksums = {'sha256': 'justamocksum'}
        resource._Resource__verify('dummy')
        mock.assert_called_with('dummy', 'sha256', 'justamocksum')

    def test_generated_url_with_cacher(self):
        tools.cfg['artifact'] = {}
        tools.cfg['artifact']['cache_url'] = '#filename#,#algorithm#,#hash#'
        resource = descriptor.UrlResource.__new__(descriptor.UrlResource)
        resource.checksums = {'sha256': 'justamocksum'}
        resource.name = 'file'
        self.assertEqual(resource._UrlResource__substitute_cache_url(),
                         'file,sha256,justamocksum')
        tools.cfg = {}

    def test_generated_url_without_cacher(self):
        resource = descriptor.UrlResource.__new__(descriptor.UrlResource)
        resource.url = 'url'
        self.assertEqual(resource._UrlResource__substitute_cache_url(),
                         resource.url)
