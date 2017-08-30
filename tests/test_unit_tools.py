import mock
import os
import requests
import unittest

from dogen import tools
from dogen.errors import DogenError
from tests import helpers

res = requests.Response()
res.status_code = 200
res.iter_content = lambda chunk_size: [b'test']

res_bad_status = requests.Response()
res_bad_status.status_code = 500


class TestTools(unittest.TestCase):

    @mock.patch('requests.get', return_value=res)
    def test_fetching_disable_ssl_verify(self, mock):
        helpers.artifact_fetcher_disable_ssl_check()
        artifact = tools.Artifact.__new__(tools.Artifact)
        artifact.name = 'file'
        artifact.artifact = 'dummy'
        artifact.fetch()
        mock.assert_called_with('dummy', stream=True, verify=False)
        tools.Artifact.ssl_verify = True
        os.remove('file')

    @mock.patch('requests.get', return_value=res_bad_status)
    def test_fetching_bad_status_code(self, mock):
        artifact = tools.Artifact.__new__(tools.Artifact)
        artifact.name = 'file'
        artifact.artifact = 'dummy'
        with self.assertRaises(DogenError):
            artifact.fetch()

    @mock.patch('requests.get', return_value=res)
    def test_fetching_file_exists(self, mock):
        with open('file', 'w') as f:
            pass
        artifact = tools.Artifact.__new__(tools.Artifact)
        artifact.name = 'file'
        artifact.artifact = 'dummy'
        artifact.fetch()
        mock.assert_not_called()
        os.remove('file')

    def test_artifact_verify_disabled_integrity_check(self):
        tools.Artifact.check_integrity = False
        artifact = tools.Artifact.__new__(tools.Artifact)
        self.assertTrue(artifact.verify())
        tools.Artifact.check_integrity = True

    @mock.patch('dogen.tools.Artifact._check_sum')
    def test_artifact_verify(self, mock):
        artifact = tools.Artifact.__new__(tools.Artifact)
        artifact.sums = {'sha256': 'justamocksum'}
        artifact.verify()
        mock.assert_called_with('sha256', 'justamocksum')

    def test_generated_url_with_cacher(self):
        os.environ['DOGEN_ARTIFACT_CACHE'] = '#filename#,#algorithm#,#hash#'
        artifact = tools.Artifact.__new__(tools.Artifact)
        artifact.sums = {'sha256': 'justamocksum'}
        artifact.name = 'file'
        artifact._generate_url()
        self.assertEqual(artifact.url,
                         'file,sha256,justamocksum')
        del os.environ['DOGEN_ARTIFACT_CACHE']

    def test_generated_url_without_cacher(self):
        artifact = tools.Artifact.__new__(tools.Artifact)
        artifact.artifact = 'url'
        artifact._generate_url()
        self.assertEqual(artifact.artifact,
                         artifact.url)

    def test_is_repo_url_path(self):
        self.assertFalse(tools.is_repo_url('/home/user/repo'))

    def test_is_repo_url_url(self):
        self.assertTrue(tools.is_repo_url('git@github.com:jboss-dockerfiles/dogen.git'))
        self.assertTrue(tools.is_repo_url('https://github.com/jboss-dockerfiles/dogen.git'))
