import logging
import pytest
import yaml

from contextlib import contextmanager

from cekit.descriptor.base import _merge_descriptors, _merge_lists
from cekit.descriptor import Descriptor, Image, Module, Overrides, Run
from cekit.errors import CekitError
from cekit import tools


class TestDescriptor(Descriptor):
    def __init__(self, descriptor):
        self.schemas = [yaml.safe_load("""type: any""")]
        super(TestDescriptor, self).__init__(descriptor)

        for key, val in descriptor.items():
            if isinstance(val, dict):
                self._descriptor[key] = TestDescriptor(val)


def test_merging_description_image():
    desc1 = Image({'name': 'foo', 'version': 1}, None)

    desc2 = Module({'name': 'mod1',
                    'description': 'mod_desc'}, None, None)

    merged = _merge_descriptors(desc1, desc2)
    assert 'description' not in merged


def test_merging_description_modules():
    desc1 = Module({'name': 'foo'}, None, None)

    desc2 = Module({'name': 'mod1',
                    'description': 'mod_desc'}, None, None)

    merged = _merge_descriptors(desc1, desc2)
    assert 'description' not in merged


def test_merging_description_override():
    desc1 = Image({'name': 'foo', 'version': 1}, None)

    desc2 = Overrides({'name': 'mod1',
                       'description': 'mod_desc'}, None)

    merged = _merge_descriptors(desc2, desc1)
    assert 'description' in merged


def test_merging_plain_descriptors():
    desc1 = TestDescriptor({'name': 'foo',
                            'a': 1,
                            'b': 2})

    desc2 = TestDescriptor({'name': 'foo',
                            'b': 5,
                            'c': 3})

    expected = TestDescriptor({'name': 'foo',
                               'a': 1,
                               'b': 2,
                               'c': 3})
    assert expected == _merge_descriptors(desc1, desc2)
    assert expected.items() == _merge_descriptors(desc1, desc2).items()


def test_merging_emdedded_descriptors():
    desc1 = TestDescriptor({'name': 'a',
                            'a': 1,
                            'b': {'name': 'b',
                                  'b1': 10,
                                  'b2': 20}})
    desc2 = TestDescriptor({'b': {'name': 'b',
                                  'b2': 50,
                                  'b3': 30},
                            'c': {'name': 'c'}})

    expected = TestDescriptor({'name': 'a',
                               'a': 1,
                               'b': {'name': 'b',
                                     'b1': 10,
                                     'b2': 20,
                                     'b3': 30},
                               'c': {'name': 'c'}})

    assert expected == _merge_descriptors(desc1, desc2)


def test_merging_plain_lists():
    list1 = [2, 3, 4, 5]
    list2 = [1, 2, 3]
    expected = [1, 2, 3, 4, 5]
    assert _merge_lists(list1, list2) == expected


def test_merging_plain_list_of_list():
    list1 = [1, 2, 3]
    list2 = [3, 4, []]
    with pytest.raises(CekitError):
        _merge_lists(list1, list2)


def test_merging_list_of_descriptors():
    desc1 = [TestDescriptor({'name': 1,
                             'a': 1,
                             'b': 2})]

    desc2 = [TestDescriptor({'name': 2,
                             'a': 123}),
             TestDescriptor({'name': 1,
                             'b': 3,
                             'c': 3})]

    expected = [TestDescriptor({'name': 2,
                                'a': 123}),
                TestDescriptor({'name': 1,
                                'a': 1,
                                'b': 2,
                                'c': 3})]

    assert expected == _merge_lists(desc1, desc2)


def test_merge_run_cmd():
    override = Run({'user': 'foo', 'cmd': ['a', 'b', 'c'], 'entrypoint': ['a', 'b']})
    image = Run({'user': 'foo', 'cmd': ['1', '2', '3'], 'entrypoint': ['1', '2']})

    override.merge(image)
    assert override['cmd'] == ['a', 'b', 'c']
    assert override['entrypoint'] == ['a', 'b']

    override = Run({})
    override.merge(image)
    assert override['cmd'] == ['1', '2', '3']
    assert override['entrypoint'] == ['1', '2']
    assert override['user'] == 'foo'


def brew_call(*args, **kwargs):
    if 'listArchives' in args[0]:
        return """
        [
          {
            "build_id": "build_id",
            "filename": "filename",
            "group_id": "group_id",
            "artifact_id": "artifact_id",
            "version": "version",
          }
        ]"""
    if 'getBuild' in args[0]:
        return """
        {
          "package_name": "package_name",
          "release": "release"
        }
        """
    return ""


def test_get_brew_url(mocker):
    mocker.patch('subprocess.check_output', side_effect=brew_call)
    url = tools.get_brew_url('aa')
    assert url == "http://download.devel.redhat.com/brewroot/packages/package_name/" + \
        "version/release/maven/group_id/artifact_id/version/filename"


@contextmanager
def mocked_dependency_handler(mocker, data="ID=fedora\nNAME=somefedora\nVERSION=123"):
    dh = None

    with mocker.mock_module.patch('cekit.tools.os.path.exists') as exists_mock:
        exists_mock.return_value = True
        with mocker.mock_module.patch('cekit.tools.open', mocker.mock_open(read_data=data)):
            dh = tools.DependencyHandler()
    try:
        yield dh
    finally:
        pass


def test_dependency_handler_init_on_unknown_env_with_os_release_file(mocker, caplog):
    with mocked_dependency_handler(mocker, ""):
        pass

    assert "You are running Cekit on an unknown platform. External dependencies suggestions may not work!" in caplog.text


def test_dependency_handler_init_on_known_env(mocker, caplog):
    caplog.set_level(logging.DEBUG)

    with mocked_dependency_handler(mocker):
        pass

    assert "You are running on known platform: somefedora 123" in caplog.text


def test_dependency_handler_init_on_unknown_env_without_os_release_file(mocker, caplog):
    caplog.set_level(logging.DEBUG)

    with mocker.mock_module.patch('cekit.tools.os.path.exists') as exists_mock:
        exists_mock.return_value = False
        tools.DependencyHandler()

    assert "You are running Cekit on an unknown platform. External dependencies suggestions may not work!" in caplog.text
    assert "You are running on known platform" not in caplog.text


def test_dependency_handler_handle_dependencies_doesnt_fail_without_deps():
    tools.DependencyHandler.__new__(
        tools.DependencyHandler)._handle_dependencies(None)


def test_dependency_handler_handle_dependencies_with_library_only(mocker, caplog):
    caplog.set_level(logging.DEBUG)

    deps = {}

    deps['python-docker'] = {
        'library': 'docker',
    }

    with mocked_dependency_handler(mocker) as handler:
        mocker.spy(handler, '_handle_dependencies')
        handler._handle_dependencies(deps)

    assert "Checking if 'python-docker' dependency is provided..." in caplog.text
    assert "Required Cekit library 'python-docker' was found as a 'docker' module!" in caplog.text
    assert "All dependencies provided!" in caplog.text


def test_dependency_handler_handle_dependencies_with_executable_only(mocker, caplog):
    caplog.set_level(logging.DEBUG)

    deps = {}

    deps['xyz'] = {
        'executable': 'xyz-aaa',
    }

    with mocked_dependency_handler(mocker) as handler:
        mocker.patch.object(handler, '_check_for_executable')
        mocker.spy(handler, '_check_for_executable')
        handler._handle_dependencies(deps)

        # pylint: disable=E1101
        assert handler._check_for_executable.call_count == 1
        handler._check_for_executable.assert_called_with('xyz', 'xyz-aaa')

    assert "Checking if 'xyz' dependency is provided..." in caplog.text
    assert "All dependencies provided!" in caplog.text


def test_dependency_handler_handle_dependencies_with_executable_only_failed(mocker, caplog):
    caplog.set_level(logging.DEBUG)

    deps = {
        'xyz': {
            'executable': 'xyz-aaa',
        }
    }
    with mocked_dependency_handler(mocker) as handler:
        with pytest.raises(CekitError, match="Cekit dependency: 'xyz' was not found, please provide the 'xyz-aaa' executable."):
            handler._handle_dependencies(deps)

    assert "Checking if 'xyz' dependency is provided..." in caplog.text


def test_dependency_handler_handle_dependencies_with_executable_and_package_on_known_platform(mocker, caplog):
    caplog.set_level(logging.DEBUG)

    deps = {}

    deps['xyz'] = {
        'executable': 'xyz-aaa',
        'package': 'python-xyz-aaa'
    }

    with mocked_dependency_handler(mocker) as handler:
        mocker.patch.object(handler, '_check_for_executable')
        mocker.spy(handler, '_check_for_executable')
        handler._handle_dependencies(deps)

        # pylint: disable=E1101
        handler._check_for_executable.assert_called_once_with('xyz', 'xyz-aaa', 'python-xyz-aaa')

    assert "Checking if 'xyz' dependency is provided..." in caplog.text
    assert "All dependencies provided!" in caplog.text


def test_dependency_handler_handle_dependencies_with_platform_specific_package(mocker, caplog):
    caplog.set_level(logging.DEBUG)

    deps = {}

    deps['xyz'] = {
        'executable': 'xyz-aaa',
        'package': 'python-xyz-aaa',
        'fedora': {
            'package': 'python-fedora-xyz-aaa'
        }
    }

    with mocked_dependency_handler(mocker) as handler:
        mocker.patch.object(handler, '_check_for_executable')
        mocker.spy(handler, '_check_for_executable')
        handler._handle_dependencies(deps)

        # pylint: disable=E1101
        handler._check_for_executable.assert_called_once_with(
            'xyz', 'xyz-aaa', 'python-fedora-xyz-aaa')

    assert "Checking if 'xyz' dependency is provided..." in caplog.text
    assert "All dependencies provided!" in caplog.text


def test_dependency_handler_check_for_executable_with_executable_only(mocker, caplog, monkeypatch):
    caplog.set_level(logging.DEBUG)

    with mocked_dependency_handler(mocker) as handler:
        monkeypatch.setenv('PATH', '/abc:/def')
        mocker.patch('os.path.exists').side_effect = [False, True]
        mocker.patch('os.access').return_value = True
        mocker.patch('os.path.isdir').return_value = False
        handler._check_for_executable('xyz', 'xyz-aaa')

    assert "Cekit dependency 'xyz' provided via the '/def/xyz-aaa' executable." in caplog.text


def test_dependency_handler_check_for_executable_with_executable_fail(mocker, monkeypatch):
    with mocked_dependency_handler(mocker) as handler:
        monkeypatch.setenv('PATH', '/abc')
        mocker.patch('os.path.exists').return_value = False
        with pytest.raises(CekitError, match=r"^Cekit dependency: 'xyz' was not found, please provide the 'xyz-aaa' executable.$"):
            handler._check_for_executable('xyz', 'xyz-aaa')


def test_dependency_handler_check_for_executable_with_executable_fail_with_package(mocker, monkeypatch):
    with mocked_dependency_handler(mocker) as handler:
        monkeypatch.setenv('PATH', '/abc')
        mocker.patch('os.path.exists').return_value = False

        with pytest.raises(CekitError, match=r"^Cekit dependency: 'xyz' was not found, please provide the 'xyz-aaa' executable. To satisfy this requrement you can install the 'package-xyz' package.$"):
            handler._check_for_executable('xyz', 'xyz-aaa', 'package-xyz')
