import argparse
import unittest
import mock
import os
import glob

from dogen.generator import Generator
from dogen.errors import Error

class TestSchemaMeta(type):
    def __new__(mcls, name, bases, dict):
        def gen_test(path, good):
            def test(self):
                args = argparse.Namespace(path=path, output="target", without_sources=None,
                                          template=None, scripts_path=None, additional_script=None,
                                          skip_ssl_verification=None)
                generator = Generator(self.log, args)
                if good:
                    generator.configure()
                else:
                    with self.assertRaises(Error):
                        generator.configure()
            return test

        for test in glob.glob(os.path.join(os.path.dirname(__file__), "schemas", "good", "*yaml")):
            test_name = "test_%s_is_valid" % os.path.splitext(os.path.basename(test))[0]
            dict[test_name] = gen_test(test, good=True)

        for test in glob.glob(os.path.join(os.path.dirname(__file__), "schemas", "bad", "*yaml")):
            test_name = "test_%s_not_valid" % os.path.splitext(os.path.basename(test))[0]
            dict[test_name] = gen_test(test, good=False)

        return type.__new__(mcls, name, bases, dict)

class TestSchema(unittest.TestCase):
    __metaclass__ = TestSchemaMeta

    def setUp(self):
        self.log = mock.Mock()
