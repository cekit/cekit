import mock
import requests
import unittest

from dogen import tools
from tests import helpers

res = requests.Response()
res.status_code = 200
res.iter_content = lambda chunk_size: [b'test']


@mock.patch('requests.get', return_value=res)
class TestTools(unittest.TestCase):

    def test_artifact_fetcher(self, mock):
        tools.artifact_fetcher('dummy')
        mock.assert_called_with('dummy', stream=True, verify=True)

    def test_artifact_fetcher_disable_ssl_verify(self, mock):
        helpers.artifact_fetcher_disable_ssl_check()
        tools.artifact_fetcher('dummy')
        mock.assert_called_with('dummy', stream=True, verify=False)
