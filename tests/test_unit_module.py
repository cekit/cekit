import mock
import unittest

from concreate import module


@mock.patch('os.walk', return_value=[('dir', None, ['module.yaml'])])
class TestModuleDiscovery(unittest.TestCase):

    @mock.patch('concreate.module.Module')
    def test_module_discovery(self, mod, _):
        module.discover_modules('repo')
        mod.assert_called_with('dir/module.yaml')

    @mock.patch('concreate.module.Module')
    def test_module_is_added_to_modules(self, mod, _):
        module.modules = []
        module.discover_modules('repo')
        self.assertEqual(len(module.modules), 1)
        module.modules = []
