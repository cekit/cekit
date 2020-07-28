# -*- encoding: utf-8 -*-

# pylint: disable=protected-access

import logging
import os
import shutil
import subprocess
import yaml

import pytest

from click.testing import CliRunner

from cekit.cli import Cekit, Map, cli
from cekit.tools import Chdir
from cekit.config import Config
from cekit.errors import CekitError
from cekit.builders.osbs import OSBSBuilder
from cekit.tools import Map

config = Config()


@pytest.fixture(autouse=True)
def reset_config():
    config.cfg['common'] = {}


config = Config()
config.cfg['common'] = {'redhat': True}

image_descriptor = {
    'schema_version': 1,
    'from': 'centos:7',
    'name': 'test/image',
    'version': '1.0',
    'labels': [{'name': 'foo', 'value': 'bar'}, {'name': 'labela', 'value': 'a'}],
    'osbs': {
            'repository': {
                'name': 'repo',
                'branch': 'branch'
            }
    }
}


def run_cekit(cwd,
              parameters=['build', '--dry-run', 'docker'],
              message=None, return_code=0):
    with Chdir(cwd):
        result = CliRunner().invoke(cli, parameters, catch_exceptions=False)

        assert result.exit_code == return_code

        if message:
            assert message in result.output

        return result


def run_osbs(descriptor, image_dir, mocker, return_code=0, build_command=None, general_command=None):
    if build_command is None:
        build_command = ['build', 'osbs']

    if general_command is None:
        general_command = ['--redhat']

    # We are mocking it, so do not require it at test time
    mocker.patch('cekit.builders.osbs.OSBSBuilder.dependencies', return_value={})
    mocker.patch('cekit.builders.osbs.OSBSBuilder._wait_for_osbs_task')
    mocker.patch('cekit.builders.osbs.DistGit.prepare')

    mocker_check_output = mocker.patch.object(subprocess, 'check_output', side_effect=[
        b"true",  # git rev-parse --is-inside-work-tree
        b"/home/repos/path",  # git rev-parse --show-toplevel
        b"branch",  # git rev-parse --abbrev-ref HEAD
        b"3b9283cb26b35511517ff5c0c3e11f490cba8feb",  # git rev-parse HEAD
        b"",  # git ls-files .
        b"",  # git ls-files --others --exclude-standard
        b"",  # git diff-files --name-only
        b"ssh://someuser@somehost.com/containers/somerepo",  # git config --get remote.origin.url
        b"3b9283cb26b35511517ff5c0c3e11f490cba8feb",  # git rev-parse HEAD
        b"1234",  # brew call --python...
        b"UUU"
    ])

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(descriptor, fd, default_flow_style=False)

    return run_cekit(image_dir, general_command + ['-v',
                                                   '--work-dir', image_dir,
                                                   '--config', 'config'] + build_command,
                     return_code=return_code)


def test_osbs_builder_with_asume_yes(tmpdir, mocker, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

    # Specifically set the decision result to False, to fail any build
    # that depends on the decision. But in case the --assume-yes switch is used
    # we should not get to this point at all. If we get, the test should fail.
    mock_decision = mocker.patch('cekit.tools.decision', return_value=False)
    mock_check_call = mocker.patch.object(subprocess, 'check_call')
    mocker.patch.object(subprocess, 'call', return_value=1)

    source_dir = tmpdir.mkdir('source')
    source_dir.mkdir('osbs').mkdir('repo')

    run_osbs(image_descriptor.copy(), str(source_dir), mocker, 0, ['build', 'osbs', '--assume-yes'])

    mock_decision.assert_not_called()

    mock_check_call.assert_has_calls(
        [
            mocker.call(['git', 'add', '--all', 'Dockerfile']),
            mocker.call(['git', 'commit', '-q', '-m',
                         'Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb']),
            mocker.call(['git', 'push', '-q', 'origin', 'branch'])
        ])

    assert "Committing with message: 'Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb'" in caplog.text
    assert "Image was built successfully in OSBS!" in caplog.text


def test_osbs_builder_with_push_with_sync_only(tmpdir, mocker, caplog):
    """
    Should sync with dist-git repository without kicking the build
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    source_dir = tmpdir.mkdir('source')
    repo_dir = source_dir.mkdir('osbs').mkdir('repo')

    mocker.patch('cekit.tools.decision', return_value=True)
    mocker.patch.object(subprocess, 'call', return_value=1)

    mock_check_call = mocker.patch.object(subprocess, 'check_call')

    descriptor = image_descriptor.copy()

    run_osbs(descriptor, str(source_dir), mocker, 0, ['build', 'osbs', '--sync-only'])

    assert os.path.exists(str(repo_dir.join('Dockerfile'))) is True

    mock_check_call.assert_has_calls(
        [
            mocker.call(['git', 'add', '--all', 'Dockerfile']),
            mocker.call(['git', 'commit', '-q', '-m',
                         'Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb']),
            mocker.call(['git', 'push', '-q', 'origin', 'branch'])
        ])

    assert "Committing with message: 'Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb'" in caplog.text
    assert "The --sync-only parameter was specified, build will not be executed, exiting" in caplog.text


def test_osbs_builder_kick_build_without_push(tmpdir, mocker, caplog):
    """
    Does not push sources to dist-git. This is the case when the
    generated files are the same as already existing in dist-git
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch('cekit.tools.decision', return_value=True)
    mocker.patch.object(subprocess, 'call', return_value=0)

    source_dir = tmpdir.mkdir('source')
    repo_dir = source_dir.mkdir('osbs').mkdir('repo')

    mock_check_call = mocker.patch.object(subprocess, 'check_call')

    descriptor = image_descriptor.copy()

    run_osbs(descriptor, str(source_dir), mocker)

    assert os.path.exists(str(repo_dir.join('Dockerfile'))) is True

    mock_check_call.assert_has_calls(
        [
            mocker.call(['git', 'add', '--all', 'Dockerfile']),
        ])

    assert "No changes made to the code, committing skipped" in caplog.text
    assert "Image was built successfully in OSBS!" in caplog.text


def test_osbs_builder_kick_build_with_push(tmpdir, mocker, caplog):
    """
    Does not push sources to dist-git. This is the case when the
    generated files are the same as already existing in dist-git
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    source_dir = tmpdir.mkdir('source')
    repo_dir = source_dir.mkdir('osbs').mkdir('repo')

    mocker.patch('cekit.tools.decision', return_value=True)
    mocker.patch.object(subprocess, 'call', return_value=1)

    mock_check_call = mocker.patch.object(subprocess, 'check_call')

    descriptor = image_descriptor.copy()

    run_osbs(descriptor, str(source_dir), mocker)

    assert os.path.exists(str(repo_dir.join('Dockerfile'))) is True

    mock_check_call.assert_has_calls(
        [
            mocker.call(['git', 'add', '--all', 'Dockerfile']),
            mocker.call(['git', 'commit', '-q', '-m',
                         'Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb']),
            mocker.call(['git', 'push', '-q', 'origin', 'branch'])
        ])

    assert "Committing with message: 'Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb'" in caplog.text
    assert "Image was built successfully in OSBS!" in caplog.text


# https://github.com/cekit/cekit/issues/504
def test_osbs_builder_add_help_file(tmpdir, mocker, caplog):
    """
    Checks if help.md file is generated and added to dist-git
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch('cekit.tools.decision', return_value=True)

    source_dir = tmpdir.mkdir('source')
    repo_dir = source_dir.mkdir('osbs').mkdir('repo')

    mocker.patch.object(subprocess, 'call', return_value=0)
    mock_check_call = mocker.patch.object(subprocess, 'check_call')

    descriptor = image_descriptor.copy()
    descriptor['help'] = {'add': True}

    run_osbs(descriptor, str(source_dir), mocker)

    assert os.path.exists(str(repo_dir.join('Dockerfile'))) is True
    assert os.path.exists(str(repo_dir.join('help.md'))) is True

    calls = [
        mocker.call(['git', 'add', '--all', 'Dockerfile']),
        mocker.call(['git', 'add', '--all', 'help.md']),
    ]

    mock_check_call.assert_has_calls(calls, any_order=True)

    assert len(mock_check_call.mock_calls) == len(calls)
    assert "Image was built successfully in OSBS!" in caplog.text


# https://github.com/cekit/cekit/issues/394
def test_osbs_builder_add_extra_files(tmpdir, mocker, caplog):
    """
    Checks if content of the 'osbs_extra' directory content is copied to dist-git
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch('cekit.tools.decision', return_value=True)

    source_dir = tmpdir.mkdir('source')
    repo_dir = source_dir.mkdir('osbs').mkdir('repo')
    dist_dir = source_dir.mkdir('osbs_extra')

    dist_dir.join('file_a').write_text(u'Some content', 'utf8')
    dist_dir.join('file_b').write_text(u'Some content', 'utf8')
    dist_dir.mkdir('child').join('other').write_text(u'Some content', 'utf8')

    os.symlink('/etc', str(dist_dir.join('a_symlink')))

    mocker.patch.object(subprocess, 'call', return_value=0)
    mock_check_call = mocker.patch.object(subprocess, 'check_call')

    run_osbs(image_descriptor, str(source_dir), mocker)

    assert os.path.exists(str(repo_dir.join('Dockerfile'))) is True
    assert os.path.exists(str(repo_dir.join('file_a'))) is True
    assert os.path.exists(str(repo_dir.join('file_b'))) is True

    calls = [
        mocker.call(['git', 'add', '--all', 'file_b']),
        mocker.call(['git', 'add', '--all', 'file_a']),
        mocker.call(['git', 'add', '--all', 'Dockerfile']),
        mocker.call(['git', 'add', '--all', 'child']),
        mocker.call(['git', 'add', '--all', 'a_symlink'])
    ]

    mock_check_call.assert_has_calls(calls, any_order=True)

    assert len(mock_check_call.mock_calls) == len(calls)
    assert "Image was built successfully in OSBS!" in caplog.text
    assert "Copying files to dist-git '{}' directory".format(str(repo_dir)) in caplog.text
    assert "Copying 'target/image/file_b' to '{}'...".format(
        os.path.join(str(repo_dir), 'file_b')) in caplog.text
    assert "Staging 'file_a'..." in caplog.text
    assert "Staging 'a_symlink'..." in caplog.text


# https://github.com/cekit/cekit/issues/394
def test_osbs_builder_add_extra_files_from_custom_dir(tmpdir, mocker, caplog):
    """
    Checks if content of the custom specified 'dist' directory content is copied to dist-git
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch('cekit.tools.decision', return_value=True)

    source_dir = tmpdir.mkdir('source')
    repo_dir = source_dir.mkdir('osbs').mkdir('repo')
    dist_dir = source_dir.mkdir('dist')

    dist_dir.join('file_a').write_text(u'Some content', 'utf8')
    dist_dir.join('file_b').write_text(u'Some content', 'utf8')
    dist_dir.mkdir('child').join('other').write_text(u'Some content', 'utf8')

    os.symlink('/etc', str(dist_dir.join('a_symlink')))

    mocker.patch.object(subprocess, 'call', return_value=0)
    mock_check_call = mocker.patch.object(subprocess, 'check_call')

    descriptor = image_descriptor.copy()

    descriptor['osbs']['extra_dir'] = 'dist'

    run_osbs(descriptor, str(source_dir), mocker)

    assert os.path.exists(str(repo_dir.join('Dockerfile'))) is True
    assert os.path.exists(str(repo_dir.join('file_a'))) is True
    assert os.path.exists(str(repo_dir.join('file_b'))) is True

    calls = [
        mocker.call(['git', 'add', '--all', 'file_b']),
        mocker.call(['git', 'add', '--all', 'file_a']),
        mocker.call(['git', 'add', '--all', 'Dockerfile']),
        mocker.call(['git', 'add', '--all', 'child']),
        mocker.call(['git', 'add', '--all', 'a_symlink'])
    ]

    mock_check_call.assert_has_calls(calls, any_order=True)

    assert len(mock_check_call.mock_calls) == len(calls)
    assert "Image was built successfully in OSBS!" in caplog.text
    assert "Copying files to dist-git '{}' directory".format(str(repo_dir)) in caplog.text
    assert "Copying 'target/image/file_b' to '{}'...".format(
        os.path.join(str(repo_dir), 'file_b')) in caplog.text
    assert "Staging 'file_a'..." in caplog.text
    assert "Staging 'a_symlink'..." in caplog.text


# https://github.com/cekit/cekit/issues/542
def test_osbs_builder_extra_default(tmpdir, mocker, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

    source_dir = tmpdir.mkdir('source')

    mocker.patch.object(subprocess, 'call', return_value=0)
    mocker.patch.object(subprocess, 'check_call')

    shutil.copytree(
        os.path.join(os.path.dirname(__file__), 'modules'),
        os.path.join(str(source_dir), 'tests', 'modules')
    )

    descriptor = image_descriptor.copy()

    del descriptor['osbs']

    run_osbs(descriptor, str(source_dir), mocker, return_code=1)

    with open(os.path.join(str(source_dir), 'target', 'image.yaml'), 'r') as _file:
        effective = yaml.safe_load(_file)

    assert effective['osbs'] is not None
    assert effective['osbs']['extra_dir'] == 'osbs_extra'


def test_osbs_builder_add_files_to_dist_git_when_it_is_a_directory(tmpdir, mocker, caplog):
    mocker.patch('cekit.tools.decision', return_value=True)
    mocker.patch.object(subprocess, 'call')
    mock_check_call = mocker.patch.object(subprocess, 'check_call')

    res = mocker.Mock()
    res.getcode.return_value = 200
    res.read.side_effect = [b'test', None]

    mocker.patch('cekit.descriptor.resource.urlopen', return_value=res)
    #mocker.patch('cekit.builders.osbs.os.path.isdir', side_effect=[False, False, True])

    descriptor = image_descriptor.copy()

    descriptor['artifacts'] = [{'path': 'manifests', 'dest': '/manifests'}]

    tmpdir.mkdir('osbs').mkdir('repo').mkdir(
        '.git').join('other').write_text(u'Some content', 'utf8')

    tmpdir.mkdir('manifests')

    with open(os.path.join(str(tmpdir), 'manifests', 'some-manifest-file.yaml'), 'w') as _file:
        _file.write("CONTENT")

    run_osbs(descriptor, str(tmpdir), mocker)

    calls = [
        mocker.call(['git', 'push', '-q', 'origin', 'branch']),
        mocker.call(['git', 'commit', '-q', '-m',
                     'Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb']),
        mocker.call(['git', 'add', '--all', 'Dockerfile']),
        mocker.call(['git', 'add', '--all', 'manifests'])
    ]

    mock_check_call.assert_has_calls(calls, any_order=True)
    assert len(mock_check_call.mock_calls) == len(calls)
    assert "Skipping '.git' directory" in caplog.text
    assert "Staging 'manifests'..." in caplog.text


def test_osbs_builder_add_files_to_dist_git_without_dotgit_directory(tmpdir, mocker, caplog):
    mocker.patch('cekit.tools.decision', return_value=True)
    mocker.patch.object(subprocess, 'call')
    mock_check_call = mocker.patch.object(subprocess, 'check_call')

    res = mocker.Mock()
    res.getcode.return_value = 200
    res.read.side_effect = [b'test', None]

    mocker.patch('cekit.descriptor.resource.urlopen', return_value=res)

    repo_dir = tmpdir.mkdir('osbs').mkdir('repo').mkdir(
        '.git').join('other').write_text(u'Some content', 'utf8')

    descriptor = image_descriptor.copy()

    descriptor['artifacts'] = [{'url': 'https://foo/bar.jar'}]

    run_osbs(descriptor, str(tmpdir), mocker)

    calls = [
        mocker.call(['git', 'push', '-q', 'origin', 'branch']),
        mocker.call(['git', 'commit', '-q', '-m',
                     'Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb']),
        mocker.call(['git', 'add', '--all', 'Dockerfile'])
    ]

    mock_check_call.assert_has_calls(calls, any_order=True)
    assert len(mock_check_call.mock_calls) == len(calls)
    assert "Skipping '.git' directory" in caplog.text


def test_osbs_builder_with_koji_target_based_on_branch(tmpdir, mocker, caplog):
    mocker.patch('cekit.tools.decision', return_value=True)
    mocker.patch('cekit.descriptor.resource.urlopen')
    mocker.patch.object(subprocess, 'call')
    mocker.patch.object(subprocess, 'check_call')

    tmpdir.mkdir('osbs').mkdir('repo').mkdir(
        '.git').join('other').write_text(u'Some content', 'utf8')

    descriptor = image_descriptor.copy()

    run_osbs(descriptor, str(tmpdir), mocker)

    assert "About to execute '/usr/bin/brew call --python buildContainer --kwargs {'src': 'git://somehost.com/containers/somerepo#3b9283cb26b35511517ff5c0c3e11f490cba8feb', 'target': 'branch-containers-candidate', 'opts': {'scratch': True, 'git_branch': 'branch', 'yum_repourls': []}}'." in caplog.text


def test_osbs_builder_with_koji_target_in_descriptor(tmpdir, mocker, caplog):
    mocker.patch('cekit.tools.decision', return_value=True)
    mocker.patch('cekit.descriptor.resource.urlopen')
    mocker.patch.object(subprocess, 'call')
    mocker.patch.object(subprocess, 'check_call')

    tmpdir.mkdir('osbs').mkdir('repo').mkdir(
        '.git').join('other').write_text(u'Some content', 'utf8')

    descriptor = image_descriptor.copy()

    descriptor['osbs']['koji_target'] = 'some-target'

    run_osbs(descriptor, str(tmpdir), mocker)

    assert "About to execute '/usr/bin/brew call --python buildContainer --kwargs {'src': 'git://somehost.com/containers/somerepo#3b9283cb26b35511517ff5c0c3e11f490cba8feb', 'target': 'some-target', 'opts': {'scratch': True, 'git_branch': 'branch', 'yum_repourls': []}}'." in caplog.text


def test_osbs_builder_with_fetch_artifacts_file_creation(tmpdir, mocker, caplog):
    """
    Checks whether the fetch-artifacts-url.yaml file is generatored.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch('cekit.tools.decision', return_value=True)
    mocker.patch('cekit.descriptor.resource.urlopen')
    mocker.patch('cekit.generator.osbs.get_brew_url', return_value='http://random.url/path')
    mocker.patch.object(subprocess, 'check_output')
    mocker.patch('cekit.builders.osbs.DistGit.push')

    tmpdir.mkdir('osbs').mkdir('repo')

    tmpdir.join('osbs').join('repo').join(
        'fetch-artifacts-url.yaml').write_text(u'Some content', 'utf8')

    with Chdir(os.path.join(str(tmpdir), 'osbs', 'repo')):
        subprocess.call(["git", "init"])
        subprocess.call(["git", "add", "fetch-artifacts-url.yaml"])
        subprocess.call(["git", "commit", "-m", "Dummy"])

    descriptor = image_descriptor.copy()

    descriptor['artifacts'] = [
        {'name': 'artifact_name', 'md5': '123456'}
    ]

    run_osbs(descriptor, str(tmpdir), mocker)

    with open(os.path.join(str(tmpdir), 'target', 'image', 'fetch-artifacts-url.yaml'), 'r') as _file:
        fetch_artifacts = yaml.safe_load(_file)

    assert len(fetch_artifacts) == 1
    assert fetch_artifacts[0] == {'md5': '123456',
                                  'target': 'artifact_name', 'url': 'http://random.url/path'}

    assert "Artifact 'artifact_name' added to fetch-artifacts-url.yaml" in caplog.text


def test_osbs_builder_with_fetch_artifacts_file_removal(tmpdir, mocker, caplog):
    """
    Checks whether the fetch-artifacts-url.yaml file is removed if exists
    and is not used anymore.

    https://github.com/cekit/cekit/issues/629
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch('cekit.tools.decision', return_value=True)
    mocker.patch('cekit.descriptor.resource.urlopen')
    mocker.patch('cekit.generator.osbs.get_brew_url', return_value='http://random.url/path')
    mocker.patch.object(subprocess, 'check_output')
    mocker.patch('cekit.builders.osbs.DistGit.push')

    tmpdir.mkdir('osbs').mkdir('repo')

    tmpdir.join('osbs').join('repo').join(
        'fetch-artifacts-url.yaml').write_text(u'Some content', 'utf8')

    with Chdir(os.path.join(str(tmpdir), 'osbs', 'repo')):
        subprocess.call(["git", "init"])
        subprocess.call(["git", "add", "fetch-artifacts-url.yaml"])
        subprocess.call(["git", "commit", "-m", "Dummy"])

    run_osbs(image_descriptor, str(tmpdir), mocker)

    assert not os.path.exists(os.path.join(str(tmpdir), 'osbs', 'repo', 'fetch-artifacts-url.yaml'))
    assert "Removing old 'fetch-artifacts-url.yaml' file" in caplog.text


@pytest.mark.parametrize('flag', [[], ['--redhat']])
def test_osbs_builder_container_yaml_existence(tmpdir, mocker, caplog, flag):
    """
    Make sure that the osbs section is properly merged.
    The evidence is that the container.yaml file is generated.

    https://github.com/cekit/cekit/issues/631
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch('cekit.tools.decision', return_value=True)
    mocker.patch('cekit.descriptor.resource.urlopen')
    mocker.patch('cekit.generator.osbs.get_brew_url', return_value='http://random.url/path')
    mocker.patch.object(subprocess, 'check_output')
    mocker.patch('cekit.builders.osbs.DistGit.push')

    tmpdir.mkdir('osbs').mkdir('repo')

    with Chdir(os.path.join(str(tmpdir), 'osbs', 'repo')):
        subprocess.call(["git", "init"])
        subprocess.call(["touch", "file"])
        subprocess.call(["git", "add", "file"])
        subprocess.call(["git", "commit", "-m", "Dummy"])

    descriptor = image_descriptor.copy()

    descriptor["osbs"]["configuration"] = {'container': {'compose': {'pulp_repos': True}}}

    run_osbs(descriptor, str(tmpdir), mocker, general_command=flag)

    assert os.path.exists(os.path.join(str(tmpdir), 'osbs', 'repo', 'container.yaml'))
