import logging
import pytest
import subprocess
import sys
import yaml

from contextlib import contextmanager

from cekit.descriptor.base import _merge_descriptors, _merge_lists
from cekit.descriptor import Descriptor, Image, Module, Overrides, Run, Osbs
from cekit.errors import CekitError
from cekit import tools

rhel_7_os_release = '''NAME="Red Hat Enterprise Linux Server"
VERSION="7.7 (Maipo)"
ID="rhel"
ID_LIKE="fedora"
VARIANT="Server"
VARIANT_ID="server"
# Some comment
VERSION_ID="7.7"
PRETTY_NAME="Red Hat Enterprise Linux Server 7.7 Beta (Maipo)"
ANSI_COLOR="0;31"
CPE_NAME="cpe:/o:redhat:enterprise_linux:7.7:beta:server"
HOME_URL="https://www.redhat.com/"
BUG_REPORT_URL="https://bugzilla.redhat.com/"

REDHAT_BUGZILLA_PRODUCT="Red Hat Enterprise Linux 7"
REDHAT_BUGZILLA_PRODUCT_VERSION=7.7
REDHAT_SUPPORT_PRODUCT="Red Hat Enterprise Linux"
REDHAT_SUPPORT_PRODUCT_VERSION="7.7 Beta"'''

rhel_8_os_release = '''NAME="Red Hat Enterprise Linux"
   # Poor comment
VERSION="8.0 (Ootpa)"
ID="rhel"
ID_LIKE="fedora"
VERSION_ID="8.0"
PLATFORM_ID="platform:el8"
PRETTY_NAME="Red Hat Enterprise Linux 8.0 (Ootpa)"
ANSI_COLOR="0;31"
CPE_NAME="cpe:/o:redhat:enterprise_linux:8.0:GA"
HOME_URL="https://www.redhat.com/"
BUG_REPORT_URL="https://bugzilla.redhat.com/"

REDHAT_BUGZILLA_PRODUCT="Red Hat Enterprise Linux 8"
REDHAT_BUGZILLA_PRODUCT_VERSION=8.0
REDHAT_SUPPORT_PRODUCT="Red Hat Enterprise Linux"
REDHAT_SUPPORT_PRODUCT_VERSION="8.0"'''


class MockedDescriptor(Descriptor):
    def __init__(self, descriptor):
        self.schema = yaml.safe_load("""type: any""")
        super(MockedDescriptor, self).__init__(descriptor)

        for key, val in descriptor.items():
            if isinstance(val, dict):
                self._descriptor[key] = MockedDescriptor(val)


def test_merging_description_image():
    desc1 = Image({'name': 'foo', 'version': 1}, None)

    desc2 = Module({'name': 'mod1', 'version': 2,
                    'description': 'mod_desc'}, None, None)

    merged = _merge_descriptors(desc1, desc2)
    assert 'description' not in merged


def test_merging_description_osbs():
    desc1 = Osbs({'extra_dir_target': 'foo'}, None)
    desc2 = Osbs({'repository': { 'name': 'repo', 'branch': 'branch'}}, None)

    merged = _merge_descriptors(desc1, desc2)
    print("\n" + repr(merged))
    assert repr(merged) == \
           "{'extra_dir_target': 'foo', 'configuration': {}, 'repository': {'name': 'repo', 'branch': 'branch'}}"
    merged = desc1.merge(desc2)
    print("\n" + repr(merged))
    assert repr(merged) == \
           "{'extra_dir_target': 'foo', 'configuration': {}, 'repository': {'name': 'repo', 'branch': 'branch'}}"

    desc1 = Osbs({'extra_dir_target': 'foo'}, None)
    desc2 = Osbs({}, None)
    merged = desc1.merge(desc2)
    print("\n" + repr(merged))
    assert repr(merged) == \
           "{'extra_dir_target': 'foo', 'configuration': {}, 'repository': {}}"

    desc1 = Osbs({'extra_dir_target': 'foo', 'repository': {'name': 'repo', 'branch': 'branch'}}, None)
    desc2 = Osbs({}, None)
    merged = desc1.merge(desc2)
    print("\n" + repr(merged))
    assert repr(merged) == \
           "{'extra_dir_target': 'foo', 'repository': {'name': 'repo', 'branch': 'branch'}, 'configuration': {}}"

    desc1 = Osbs({'extra_dir_target': 'foo', 'repository': {'name': 'foobar', 'branch': 'foobranch'}}, None)
    desc2 = Osbs({'repository': {'name': 'repo', 'branch': 'branch'}}, None)
    merged = desc1.merge(desc2)
    print("\n" + repr(merged))
    assert repr(merged) == \
           "{'extra_dir_target': 'foo', 'repository': {'name': 'repo', 'branch': 'branch'}, 'configuration': {}}"

    desc1 = Osbs({'extra_dir_target': 'foo', 'configuration': {'container': {'image_build_method': 'imagebuilder'}}}, None)
    desc2 = Osbs({}, None)
    merged = desc1.merge(desc2)
    print("\n" + repr(merged))
    assert repr(merged) == \
           "{'extra_dir_target': 'foo', 'configuration': {'container': {'image_build_method': 'imagebuilder'}}, 'repository': {}}"

    desc1 = Osbs({'extra_dir_target': 'foo', 'configuration': {'container': {'image_build_method': 'imagebuilder'}}}, None)
    desc2 = Osbs({'configuration': {'container': {'remote_source': {'repo': 'https://github.com/kiegroup/rhpam-kogito-operator'}}}}, None)
    merged = desc1.merge(desc2)
    print("\n" + repr(merged))
    assert repr(merged) == \
           "{'extra_dir_target': 'foo', 'configuration': {'container': {'remote_source': {'repo': 'https://github.com/kiegroup/rhpam-kogito-operator'}}}, 'repository': {}}"


def test_merging_description_modules():
    desc1 = Module({'name': 'foo', 'version': '1.0'}, None, None)

    desc2 = Module({'name': 'mod1', 'version': '1.0',
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
    desc1 = MockedDescriptor({'name': 'foo',
                              'a': 1,
                              'b': 2})

    desc2 = MockedDescriptor({'name': 'foo',
                              'b': 5,
                              'c': 3})

    expected = MockedDescriptor({'name': 'foo',
                                 'a': 1,
                                 'b': 2,
                                 'c': 3})
    assert expected == _merge_descriptors(desc1, desc2)
    assert expected.items() == _merge_descriptors(desc1, desc2).items()


def test_merging_emdedded_descriptors():
    desc1 = MockedDescriptor({'name': 'a',
                              'a': 1,
                              'b': {'name': 'b',
                                    'b1': 10,
                                    'b2': 20}})
    desc2 = MockedDescriptor({'b': {'name': 'b',
                                    'b2': 50,
                                    'b3': 30},
                              'c': {'name': 'c'}})

    expected = MockedDescriptor({'name': 'a',
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
    desc1 = [MockedDescriptor({'name': 1,
                               'a': 1,
                               'b': 2})]

    desc2 = [MockedDescriptor({'name': 2,
                               'a': 123}),
             MockedDescriptor({'name': 1,
                               'b': 3,
                               'c': 3})]

    expected = [MockedDescriptor({'name': 2,
                                  'a': 123}),
                MockedDescriptor({'name': 1,
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


def brew_call_ok(*args, **kwargs):
    if 'listArchives' in args[0]:
        return """
            [
            {
                "build_id": 179262,
                "version": "20100527",
                "type_name": "jar",
                "artifact_id": "oauth",
                "type_id": 1,
                "checksum": "91c7c70579f95b7ddee95b2143a49b41",
                "extra": null,
                "filename": "oauth-20100527.jar",
                "type_description": "Jar file",
                "metadata_only": false,
                "type_extensions": "jar war rar ear sar kar jdocbook jdocbook-style plugin",
                "btype": "maven",
                "checksum_type": 0,
                "btype_id": 2,
                "group_id": "net.oauth.core",
                "buildroot_id": null,
                "id": 105858,
                "size": 44209
            }
            ]""".encode("utf8")
    if 'getBuild' in args[0]:
        return """
            {
            "package_name": "net.oauth.core-oauth",
            "extra": null,
            "creation_time": "2011-09-12 05:38:16.978647",
            "completion_time": "2011-09-12 05:38:16.978647",
            "package_id": 18782,
            "id": 179262,
            "build_id": 179262,
            "epoch": null,
            "source": null,
            "state": 1,
            "version": "20100527",
            "completion_ts": 1315805896.97865,
            "owner_id": 1515,
            "owner_name": "hfnukal",
            "nvr": "net.oauth.core-oauth-20100527-1",
            "start_time": null,
            "creation_event_id": 4204830,
            "start_ts": null,
            "volume_id": 8,
            "creation_ts": 1315805896.97865,
            "name": "net.oauth.core-oauth",
            "task_id": null,
            "volume_name": "rhel-7",
            "release": "1"
            }
            """.encode("utf8")
    return "".encode("utf8")


def brew_call_ok_with_dot(*args, **kwargs):
    if 'listArchives' in args[0]:
        return """
            [
            {
                "build_id": 410568,
                "version": "1.0.4",
                "type_name": "jar",
                "artifact_id": "javax.json",
                "type_id": 1,
                "checksum": "569870f975deeeb6691fcb9bc02a9555",
                "extra": null,
                "filename": "javax.json-1.0.4.jar",
                "type_description": "Jar file",
                "metadata_only": false,
                "type_extensions": "jar war rar ear sar kar jdocbook jdocbook-style plugin",
                "btype": "maven",
                "checksum_type": 0,
                "btype_id": 2,
                "group_id": "org.glassfish",
                "buildroot_id": null,
                "id": 863130,
                "size": 85147
            }
            ]""".encode("utf8")
    if 'getBuild' in args[0]:
        return """
            {
            "package_name": "org.glassfish-javax.json",
            "extra": null,
            "creation_time": "2015-01-10 16:28:59.105878",
            "completion_time": "2015-01-10 16:28:59.105878",
            "package_id": 49642,
            "id": 410568,
            "build_id": 410568,
            "epoch": null,
            "source": null,
            "state": 1,
            "version": "1.0.4",
            "completion_ts": 1420907339.10588,
            "owner_id": 2679,
            "owner_name": "pgallagh",
            "nvr": "org.glassfish-javax.json-1.0.4-1",
            "start_time": null,
            "creation_event_id": 10432034,
            "start_ts": null,
            "volume_id": 8,
            "creation_ts": 1420907339.10588,
            "name": "org.glassfish-javax.json",
            "task_id": null,
            "volume_name": "rhel-7",
            "release": "1"
            }
            """.encode("utf8")
    return "".encode("utf8")


def brew_call_removed(*args, **kwargs):
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
        ]""".encode("utf8")
    if 'getBuild' in args[0]:
        return """
        {
          "package_name": "package_name",
          "release": "release",
          "state": 2
        }
        """.encode("utf8")
    return "".encode("utf8")


def test_get_brew_url(mocker):
    mocker.patch('subprocess.check_output', side_effect=brew_call_ok)
    url = tools.get_brew_url('aa')
    assert url == "http://download.devel.redhat.com/brewroot/packages/net.oauth.core-oauth/20100527/1/maven/net/oauth/core/oauth/20100527/oauth-20100527.jar"


def test_get_brew_url_when_build_was_removed(mocker):
    mocker.patch('subprocess.check_output', side_effect=brew_call_removed)

    with pytest.raises(CekitError) as excinfo:
        tools.get_brew_url('aa')

    assert 'Artifact with checksum aa was found in Koji metadata but the build is in incorrect state (DELETED) making the artifact not available for downloading anymore' in str(
        excinfo.value)


# https://github.com/cekit/cekit/issues/502
def test_get_brew_url_no_kerberos(mocker, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

    kerberos_error = subprocess.CalledProcessError(1, 'CMD')
    kerberos_error.output = "2019-05-06 14:58:44,502 [ERROR] koji: AuthError: unable to obtain a session"

    mocker.patch('subprocess.check_output', side_effect=kerberos_error)

    with pytest.raises(CekitError) as excinfo:
        tools.get_brew_url('aa')

    assert 'Could not fetch archives for checksum aa' in str(excinfo.value)
    assert "Brew authentication failed, please make sure you have a valid Kerberos ticket" in caplog.text


# https://github.com/cekit/cekit/issues/531
def test_get_brew_url_with_artifact_containing_dot(mocker):
    mocker.patch('subprocess.check_output', side_effect=brew_call_ok_with_dot)
    url = tools.get_brew_url('aa')
    assert url == "http://download.devel.redhat.com/brewroot/packages/org.glassfish-javax.json/1.0.4/1/maven/org/glassfish/javax.json/1.0.4/javax.json-1.0.4.jar"


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

    assert "You are running CEKit on an unknown platform. External dependencies suggestions may not work!" in caplog.text


# https://github.com/cekit/cekit/issues/450
def test_dependency_handler_on_rhel_7(mocker, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

    with mocked_dependency_handler(mocker, rhel_7_os_release):
        pass

    assert "You are running on known platform: Red Hat Enterprise Linux Server 7.7 (Maipo)" in caplog.text


# https://github.com/cekit/cekit/issues/450
def test_dependency_handler_on_rhel_8(mocker, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

    with mocked_dependency_handler(mocker, rhel_8_os_release):
        pass

    assert "You are running on known platform: Red Hat Enterprise Linux 8.0 (Ootpa)" in caplog.text


def test_dependency_handler_init_on_known_env(mocker, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

    with mocked_dependency_handler(mocker):
        pass

    assert "You are running on known platform: somefedora 123" in caplog.text


def test_dependency_handler_init_on_unknown_env_without_os_release_file(mocker, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

    with mocker.mock_module.patch('cekit.tools.os.path.exists') as exists_mock:
        exists_mock.return_value = False
        tools.DependencyHandler()

    assert "You are running CEKit on an unknown platform. External dependencies suggestions may not work!" in caplog.text
    assert "You are running on known platform" not in caplog.text


def test_dependency_handler_handle_dependencies_doesnt_fail_without_deps():
    tools.DependencyHandler.__new__(
        tools.DependencyHandler)._handle_dependencies(None)


def test_dependency_handler_handle_dependencies_with_library_only(mocker, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

    deps = {}

    deps['python-docker'] = {
        'library': 'docker',
    }

    with mocked_dependency_handler(mocker) as handler:
        mocker.spy(handler, '_handle_dependencies')
        handler._handle_dependencies(deps)

    assert "Checking if 'python-docker' dependency is provided..." in caplog.text
    assert "Required CEKit library 'python-docker' was found as a 'docker' module!" in caplog.text
    assert "All dependencies provided!" in caplog.text


def test_dependency_handler_handle_dependencies_with_executable_only(mocker, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

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
    caplog.set_level(logging.DEBUG, logger="cekit")

    deps = {
        'xyz': {
            'executable': 'xyz-aaa',
        }
    }
    with mocked_dependency_handler(mocker) as handler:
        with pytest.raises(CekitError, match="CEKit dependency: 'xyz' was not found, please provide the 'xyz-aaa' executable."):
            handler._handle_dependencies(deps)

    assert "Checking if 'xyz' dependency is provided..." in caplog.text


def test_dependency_handler_handle_dependencies_with_executable_and_package_on_known_platform(mocker, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

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
    caplog.set_level(logging.DEBUG, logger="cekit")

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
    caplog.set_level(logging.DEBUG, logger="cekit")

    with mocked_dependency_handler(mocker) as handler:
        monkeypatch.setenv('PATH', '/abc:/def')
        mocker.patch('os.path.exists').side_effect = [False, True]
        mocker.patch('os.access').return_value = True
        mocker.patch('os.path.isdir').return_value = False
        handler._check_for_executable('xyz', 'xyz-aaa')

    assert "CEKit dependency 'xyz' provided via the '/def/xyz-aaa' executable." in caplog.text


def test_dependency_handler_check_for_executable_with_executable_fail(mocker, monkeypatch):
    with mocked_dependency_handler(mocker) as handler:
        monkeypatch.setenv('PATH', '/abc')
        mocker.patch('os.path.exists').return_value = False
        with pytest.raises(CekitError, match=r"^CEKit dependency: 'xyz' was not found, please provide the 'xyz-aaa' executable.$"):
            handler._check_for_executable('xyz', 'xyz-aaa')


def test_dependency_handler_check_for_executable_with_executable_fail_with_package(mocker, monkeypatch):
    with mocked_dependency_handler(mocker) as handler:
        monkeypatch.setenv('PATH', '/abc')
        mocker.patch('os.path.exists').return_value = False

        with pytest.raises(CekitError, match=r"^CEKit dependency: 'xyz' was not found, please provide the 'xyz-aaa' executable. To satisfy this requirement you can install the 'package-xyz' package.$"):
            handler._check_for_executable('xyz', 'xyz-aaa', 'package-xyz')


def test_handle_core_dependencies_no_certifi(mocker, caplog):
    sys.modules['certifi'] = None

    with mocked_dependency_handler(mocker) as handler:
        handler.handle_core_dependencies()

    assert "The certifi library (https://certifi.io/) was found, depending on the operating system configuration this may result in certificate validation issues" not in caplog.text


def test_handle_core_dependencies_with_certifi(mocker, caplog):
    mock_certifi = mocker.Mock()
    mock_certifi.where.return_value = 'a/path.pem'

    sys.modules['certifi'] = mock_certifi

    with mocked_dependency_handler(mocker) as handler:
        handler.handle_core_dependencies()

    assert "The certifi library (https://certifi.io/) was found, depending on the operating system configuration this may result in certificate validation issues" in caplog.text
    assert "Certificate Authority (CA) bundle in use: 'a/path.pem'" in caplog.text
