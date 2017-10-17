from concreate import module


def test_module_discovery(mocker):
    mocker.patch('os.walk', return_value=[('dir', None, ['module.yaml'])])

    mod = mocker.patch('concreate.module.Module')

    module.discover_modules('repo')
    mod.assert_called_with('dir/module.yaml')


def test_module_is_added_to_modules(mocker):
    mocker.patch('os.walk', return_value=[('dir', None, ['module.yaml'])])
    mocker.patch('concreate.module.Module')

    module.modules = []
    module.discover_modules('repo')
    assert len(module.modules) == 1
    module.modules = []
