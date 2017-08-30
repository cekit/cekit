import mock
import unittest

from dogen import module


@mock.patch('subprocess.check_output')
class TestModuleFetching(unittest.TestCase):

    def test_repository_dir_is_constructed_properly(self, mock):
        self.assertEqual(module.clone_module_repository('url/repo', 'ref', 'dir'),
                         'dir/repo-ref')

    def test_git_clone(self, mock):
        module.clone_module_repository('url', 'ref', 'dir')
        mock.assert_called_with(['git',
                                 'clone',
                                 '--depth',
                                 '1',
                                 'url',
                                 'dir/url-ref',
                                 '-b',
                                 'ref'],
                                stderr=-2)


@mock.patch('os.walk', return_value=[('dir', None, ['module.yaml'])])
class TestModuleDiscovery(unittest.TestCase):

    @mock.patch('dogen.module.Module')
    def test_module_discovery(self, mod, _):
        module.discover_modules('repo')
        mod.assert_called_with('dir/module.yaml')

    @mock.patch('dogen.module.Module')
    def test_module_is_added_to_modules(self, mod, _):
        module.modules = []
        module.discover_modules('repo')
        self.assertEqual(len(module.modules), 1)
        module.modules = []
