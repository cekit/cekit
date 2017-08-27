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


class TestArtifact(unittest.TestCase):

    @mock.patch('requests.get', return_value=res)
    def test_fetching_disable_ssl_verify(self, mock):
        helpers.artifact_fetcher_disable_ssl_check()
        artifact = tools.Artifact.__new__(tools.Artifact)
        artifact.name = 'file'
        artifact.url = 'dummy'
        artifact.fetch()
        mock.assert_called_with('dummy', stream=True, verify=False)
        tools.Artifact.ssl_verify = True

    @mock.patch('requests.get', return_value=res_bad_status)
    def test_fetching_bad_status_code(self, mock):
        artifact = tools.Artifact.__new__(tools.Artifact)
        artifact.name = 'file'
        artifact.url = 'dummy'
        with self.assertRaises(DogenError):
            artifact.fetch()

    def test_artifact_check_sums_disabled(self):
        tools.Artifact.check_integrity = False
        artifact = tools.Artifact.__new__(tools.Artifact)
        self.assertTrue(artifact.check_sums())
        tools.Artifact.check_integrity = True

    @mock.patch('dogen.tools.Artifact._check_sum')
    def test_artifact_check_sums(self, mock):
        artifact = tools.Artifact.__new__(tools.Artifact)
        artifact.sums = {'sha256': 'justamocksum'}
        artifact.check_sums()
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
        
        

        
