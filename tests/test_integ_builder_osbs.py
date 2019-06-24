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
    'from': 'centos:latest',
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


def run_osbs(descriptor, image_dir, mocker, return_code=0):
    # We are mocking it, so do not require it at test time
    mocker.patch('cekit.builders.osbs.OSBSBuilder.dependencies', return_value={})
    mocker.patch('cekit.builders.osbs.OSBSBuilder._wait_for_osbs_task')
    mocker.patch('cekit.builders.osbs.DistGit.clean')
    mocker.patch('cekit.builders.osbs.DistGit.prepare')
    mocker.patch('cekit.tools.decision', return_value=True)

    mocker_check_call = mocker.patch.object(subprocess, 'check_output', side_effect=[
        b"true",  # git rev-parse --is-inside-work-tree
        b"/home/repos/path",  # git rev-parse --show-toplevel
        b"branch",  # git rev-parse --abbrev-ref HEAD
        b"3b9283cb26b35511517ff5c0c3e11f490cba8feb",  # git rev-parse HEAD
        b"",  # git ls-files --others --exclude-standard
        b"",  # git diff-files --name-only
        b"ssh://someuser@somehost.com/containers/somerepo",  # git config --get remote.origin.url
        b"3b9283cb26b35511517ff5c0c3e11f490cba8feb",  # git rev-parse HEAD
        b"1234",  # brew call --python...
    ])

    with open(os.path.join(image_dir, 'config'), 'w') as fd:
        fd.write("[common]\n")
        fd.write("redhat = True")

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(descriptor, fd, default_flow_style=False)

    return run_cekit(image_dir, ['-v',
                                 '--work-dir', image_dir,
                                 '--config', 'config',
                                 'build',
                                 'osbs'],
                     return_code=return_code)


def test_osbs_builder_kick_build_without_push(tmpdir, mocker, caplog):
    """
    Does not push sources to dist-git. This is the case when the
    generated files are the same as already existing in dist-git
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

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

    assert "Commiting with message: 'Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb'" in caplog.text
    assert "Image was built successfully in OSBS!" in caplog.text


# https://github.com/cekit/cekit/issues/504
def test_osbs_builder_add_help_file(tmpdir, mocker, caplog):
    """
    Checks if help.md file is generated and added to dist-git
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

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
