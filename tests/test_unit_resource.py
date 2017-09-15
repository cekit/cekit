
import mock
import os
import requests
import unittest

from concreate import resource
from concreate import tools
from concreate.errors import ConcreateError


@mock.patch('subprocess.check_output')
class TestGitResource(unittest.TestCase):

    def test_repository_dir_is_constructed_properly(self, mock):
        res = resource.GitResource(
            {'git': {'url': 'url/repo', 'ref': 'ref'}})
        self.assertEqual(res.copy('dir'), 'dir/repo-ref')

    def test_git_clone(self, mock):
        res = resource.GitResource(
            {'git': {'url': 'url', 'ref': 'ref'}})
        res.copy('dir')
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
        res = resource.UrlResource(
            {'name': 'file', 'url': 'https:///dummy'})
        try:
            res.copy()
        except:
            pass
        mock.assert_called_with('https:///dummy', stream=True, verify=False)
        tools.cfg['common']['ssl_verify'] = "True"
        os.remove('file')
        tools.cfg = {}

    @mock.patch('requests.get', return_value=res_bad_status)
    def test_fetching_bad_status_code(self, mock):
        res = resource.UrlResource(
            {'name': 'file', 'url': 'http:///dummy'})
        with self.assertRaises(ConcreateError):
            res.copy()

    @mock.patch('requests.get', return_value=res)
    def test_fetching_file_exists_but_used_as_is(self, mock):
        """
        It should not download the file, because we didn't
        specify any hash algorithm, so integrity checking is
        implicitly disabled here.
        """
        with open('file', 'w') as f:  # noqa: F841
            pass
        res = resource.UrlResource(
            {'name': 'file', 'url': 'http:///dummy'})
        res.copy()
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
        res = resource.UrlResource(
            {'name': 'file', 'url': 'http:///dummy', 'md5': '123456'})
        with self.assertRaises(ConcreateError):
            # Checksum will fail, because the "downloaded" file
            # will not have md5 equal to 123456. We need investigate
            # mocking of requests get calls to do it properly
            res.copy()
        mock.assert_called_with('http:///dummy', verify=True, stream=True)
        os.remove('file')

    def test_resource_verify_disabled_integrity_check(self):
        resource.Resource.check_integrity = False
        res = resource.Resource.__new__(resource.Resource)
        res.checksums = {}
        self.assertTrue(res._Resource__verify('dummy'))
        resource.Resource.check_integrity = True

    @mock.patch('concreate.resource.Resource._Resource__check_sum')
    def test_resource_verify(self, mock):
        res = resource.Resource.__new__(resource.Resource)
        res.checksums = {'sha256': 'justamocksum'}
        res._Resource__verify('dummy')
        mock.assert_called_with('dummy', 'sha256', 'justamocksum')

    def test_generated_url_with_cacher(self):
        tools.cfg['common'] = {}
        tools.cfg['common']['cache_url'] = '#filename#,#algorithm#,#hash#'
        res = resource.UrlResource.__new__(resource.UrlResource)
        res.checksums = {'sha256': 'justamocksum'}
        res.name = 'file'
        self.assertEqual(res._Resource__substitute_cache_url('file'),
                         'file,sha256,justamocksum')
        tools.cfg = {}

    def test_generated_url_without_cacher(self):
        res = resource.UrlResource.__new__(resource.UrlResource)
        res.url = 'url'
        self.assertEqual(res._Resource__substitute_cache_url('url'),
                         'url')
