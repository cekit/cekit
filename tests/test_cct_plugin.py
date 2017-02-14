import tempfile
import unittest
import shutil

from dogen.plugins import cct

# minimal fake dogen object
class MockDogen():
    def __init__(self):
        self.log = 0
        self.descriptor = 0
        self.output = ""

class TestCCTPlugin(unittest.TestCase):
    def setUp(self):
        self.workdir = tempfile.mkdtemp(prefix='test_cct_plugin')
        self.cct = cct.CCT(dogen=MockDogen(), args=None)

    def teardown(self):
        shutil.rmtree(self.workdir)
