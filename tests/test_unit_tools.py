import mock
import os
import requests
import unittest

from concreate import tools
from concreate.errors import ConcreateError

res = requests.Response()
res.status_code = 200
res.iter_content = lambda chunk_size: [b'test']

res_bad_status = requests.Response()
res_bad_status.status_code = 500


class TestTools(unittest.TestCase):
    def setUp(self):
        tools.cfg = {}

    @mock.patch('requests.get', return_value=res)
    def test_fetching_disable_ssl_verify(self, mock):
        tools.cfg['common'] = {}
        tools.cfg['common']['ssl_verify'] = "False"
        artifact = tools.Artifact({'name': 'file', 'artifact': 'dummy'})
        artifact.fetch()
        mock.assert_called_with('dummy', stream=True, verify=False)
        tools.Artifact.ssl_verify = True
        os.remove('file')
        tools.cfg = {}

    @mock.patch('requests.get', return_value=res_bad_status)
    def test_fetching_bad_status_code(self, mock):
        artifact = tools.Artifact({'name': 'file', 'artifact': 'dummy'})
        with self.assertRaises(ConcreateError):
            artifact.fetch()

    @mock.patch('requests.get', return_value=res)
    def test_fetching_file_exists_but_used_as_is(self, mock):
        """
        It should not download the file, because we didn't
        specify any hash algorithm, so integrity checking is
        implicitly disabled here.
        """
        with open('file', 'w') as f:
            pass
        artifact = tools.Artifact({'name': 'file', 'artifact': 'dummy'})
        artifact.fetch()
        mock.assert_not_called()
        os.remove('file')

    @mock.patch('requests.get', return_value=res)
    def test_fetching_file_exists_fetched_again(self, mock):
        """
        It should download the file again, because available
        file locally doesn't match checksum.
        """
        with open('file', 'w') as f:
            pass
        artifact = tools.Artifact({'name': 'file', 'artifact': 'dummy', 'md5': '123456'})
        with self.assertRaises(ConcreateError):
            # Checksum will fail, because the "downloaded" file
            # will not have md5 equal to 123456. We need investigate
            # mocking of requests get calls to do it properly
            artifact.fetch()
        mock.assert_called_with('dummy', stream=True, verify=True)
        os.remove('file')

    def test_artifact_verify_disabled_integrity_check(self):
        tools.Artifact.check_integrity = False
        artifact = tools.Artifact.__new__(tools.Artifact)
        self.assertTrue(artifact.verify())
        tools.Artifact.check_integrity = True

    @mock.patch('concreate.tools.Artifact._check_sum')
    def test_artifact_verify(self, mock):
        artifact = tools.Artifact.__new__(tools.Artifact)
        artifact.sums = {'sha256': 'justamocksum'}
        artifact.verify()
        mock.assert_called_with('sha256', 'justamocksum')

    def test_generated_url_with_cacher(self):
        tools.cfg['artifact'] = {}
        tools.cfg['artifact']['cache_url'] = '#filename#,#algorithm#,#hash#'
        artifact = tools.Artifact.__new__(tools.Artifact)
        artifact.sums = {'sha256': 'justamocksum'}
        artifact.name = 'file'
        artifact._generate_url()
        self.assertEqual(artifact.url,
                         'file,sha256,justamocksum')
        tools.cfg = {}

    def test_generated_url_without_cacher(self):
        artifact = tools.Artifact.__new__(tools.Artifact)
        artifact.artifact = 'url'
        artifact._generate_url()
        self.assertEqual(artifact.artifact,
                         artifact.url)

    def test_is_repo_url_path(self):
        self.assertFalse(tools.is_repo_url('/home/user/repo'))

    def test_is_repo_url_url(self):
        self.assertTrue(tools.is_repo_url('git@github.com:jboss-dockerfiles/concreate.git'))
        self.assertTrue(tools.is_repo_url('https://github.com/jboss-dockerfiles/concreate.git'))
