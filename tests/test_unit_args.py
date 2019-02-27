import os
import pytest
import sys

from cekit.cli import Cekit, cli

from click.testing import CliRunner


@pytest.mark.parametrize('args,commands,parameters', [
    # Check custom target
    (
        ['--redhat', 'build', 'docker'],
        ['cli', 'build', 'docker'],
        {'descriptor': 'image.yaml', 'verbose': False, 'work_dir': '~/.cekit', 'config': '~/.cekit/config', 'redhat': True,
            'target': 'target', 'package_manager': 'yum', 'dry_run': False, 'overrides': (), 'addhelp': None, 'pull': False, 'no_squash': False, 'tags': ()}
    ),
    # Check custom target
    (
        ['--target', 'custom-target', 'build', 'docker'],
        ['cli', 'build', 'docker'],
        {'descriptor': 'image.yaml', 'verbose': False, 'work_dir': '~/.cekit', 'config': '~/.cekit/config', 'redhat': False,
            'target': 'custom-target', 'package_manager': 'yum', 'dry_run': False, 'overrides': (), 'addhelp': None, 'pull': False, 'no_squash': False, 'tags': ()}
    ),
    # Check custom work dir
    (
        ['--work-dir', 'custom-workdir', 'build', 'docker'],
        ['cli', 'build', 'docker'],
        {'descriptor': 'image.yaml', 'verbose': False, 'work_dir': 'custom-workdir', 'config': '~/.cekit/config', 'redhat': False,
            'target': 'target', 'package_manager': 'yum', 'dry_run': False, 'overrides': (), 'addhelp': None, 'pull': False, 'no_squash': False, 'tags': ()}
    ),
    # Check custom config file
    (
        ['--config', 'custom-config', 'build', 'docker'],
        ['cli', 'build', 'docker'],
        {'descriptor': 'image.yaml', 'verbose': False, 'work_dir': '~/.cekit', 'config': 'custom-config', 'redhat': False,
            'target': 'target', 'package_manager': 'yum', 'dry_run': False, 'overrides': (), 'addhelp': None, 'pull': False, 'no_squash': False, 'tags': ()}
    ),
    # Test default values for Docker builder
    (
        ['build', 'docker'],
        ['cli', 'build', 'docker'],
        {'descriptor': 'image.yaml', 'verbose': False, 'work_dir': '~/.cekit', 'config': '~/.cekit/config', 'redhat': False,
            'target': 'target', 'package_manager': 'yum', 'dry_run': False, 'overrides': (), 'addhelp': None, 'pull': False, 'no_squash': False, 'tags': ()}
    ),
    # Test overrides
    (
        ['build', '--overrides', 'foo', '--overrides-file', 'bar', 'docker'],
        ['cli', 'build', 'docker'],
        {'descriptor': 'image.yaml', 'verbose': False, 'work_dir': '~/.cekit', 'config': '~/.cekit/config', 'redhat': False,
            'target': 'target', 'package_manager': 'yum', 'dry_run': False, 'overrides': ('foo', 'bar'), 'addhelp': None, 'pull': False, 'no_squash': False, 'tags': ()}
    ),
    # Test default values for OSBS builder
    (
        ['build', 'osbs'],
        ['cli', 'build', 'osbs'],
        {'descriptor': 'image.yaml', 'verbose': False, 'work_dir': '~/.cekit', 'config': '~/.cekit/config', 'redhat': False, 'target': 'target', 'koji_target': None, 'package_manager': 'yum',
            'dry_run': False, 'overrides': (), 'addhelp': None, 'release': False, 'tech_preview': False, 'user': None, 'nowait': False, 'stage': False, 'commit_message': None}
    ),
    # Test setting user for OSBS
    (
        ['build', 'osbs', '--user', 'SOMEUSER'],
        ['cli', 'build', 'osbs'],
        {'descriptor': 'image.yaml', 'verbose': False, 'work_dir': '~/.cekit', 'config': '~/.cekit/config', 'redhat': False, 'target': 'target', 'koji_target': None, 'package_manager': 'yum',
            'dry_run': False, 'overrides': (), 'addhelp': None, 'release': False, 'tech_preview': False, 'user': 'SOMEUSER', 'nowait': False, 'stage': False, 'commit_message': None}
    ),
    # Test setting stage environment for OSBS
    (
        ['build', 'osbs', '--stage'],
        ['cli', 'build', 'osbs'],
        {'descriptor': 'image.yaml', 'verbose': False, 'work_dir': '~/.cekit', 'config': '~/.cekit/config', 'redhat': False, 'target': 'target', 'koji_target': None, 'package_manager': 'yum',
            'dry_run': False, 'overrides': (), 'addhelp': None, 'release': False, 'tech_preview': False, 'user': None, 'nowait': False, 'stage': True, 'commit_message': None}
    ),
    # Test setting nowait for OSBS
    (
        ['build', 'osbs', '--nowait'],
        ['cli', 'build', 'osbs'],
        {'descriptor': 'image.yaml', 'verbose': False, 'work_dir': '~/.cekit', 'config': '~/.cekit/config', 'redhat': False, 'target': 'target', 'koji_target': None, 'package_manager': 'yum',
            'dry_run': False, 'overrides': (), 'addhelp': None, 'release': False, 'tech_preview': False, 'user': None, 'nowait': True, 'stage': False, 'commit_message': None}
    ),
    (
        ['test', 'image:1.0'],
        ['cli', 'test'],
        {'descriptor': 'image.yaml', 'verbose': False, 'work_dir': '~/.cekit', 'config': '~/.cekit/config', 'redhat': False,
            'target': 'target', 'package_manager': 'yum', 'image': 'image:1.0', 'steps_url': 'https://github.com/cekit/behave-test-steps.git', 'wip': False, 'names': ()}
    ),
    (
        ['build', 'docker', '--pull'],
        ['cli', 'build', 'docker'],
        {'descriptor': 'image.yaml', 'verbose': False, 'work_dir': '~/.cekit', 'config': '~/.cekit/config', 'redhat': False,
            'target': 'target', 'package_manager': 'yum', 'dry_run': False, 'overrides': (), 'addhelp': None, 'pull': True, 'no_squash': False, 'tags': ()}
    ),
])
def test_args_command(mocker, args, commands, parameters):
    cekit = mocker.patch('cekit.cli.Cekit')
    CliRunner().invoke(cli, args, catch_exceptions=False)
    cekit.assert_called_once_with(commands, parameters)


def test_args_not_valid_command(mocker):
    result = CliRunner().invoke(cli, ['explode'], catch_exceptions=False)

    assert isinstance(result.exception, SystemExit)
    assert 'No such command "explode"' in result.output
    assert result.exit_code == 2


@pytest.mark.parametrize('engine,params', [
    ('osbs', {'config': '~/.cekit/config', 'user': None, 'package_manager': 'yum', 'target': 'target', 'koji_target': None, 'overrides': (), 'dry_run': False, 'descriptor': 'image.yaml', 'release': False,
              'work_dir': '~/.cekit', 'commit_message': None, 'tech_preview': False, 'redhat': False, 'addhelp': None, 'stage': False, 'nowait': False, 'verbose': False}),
    ('docker', {'descriptor': 'image.yaml', 'work_dir': '~/.cekit', 'config': '~/.cekit/config', 'redhat': False, 'addhelp': None, 'dry_run': False,
                'package_manager': 'yum', 'target': 'target', 'overrides': (), 'tags': (), 'pull': False, 'verbose': False, 'no_squash': False}),
    ('buildah', {'descriptor': 'image.yaml', 'work_dir': '~/.cekit', 'config': '~/.cekit/config', 'redhat': False, 'addhelp': None,
                 'package_manager': 'yum', 'target': 'target', 'overrides': (), 'tags': (), 'pull': False, 'verbose': False, 'dry_run': False}),
])
def test_args_build_engine(mocker, engine, params):
    cekit = mocker.patch('cekit.cli.Cekit')
    CliRunner().invoke(cli, ['build', engine], catch_exceptions=False)
    cekit.assert_called_once_with(['cli', 'build', engine], params)


def test_args_invalid_build_engine(mocker):
    result = CliRunner().invoke(cli, ['build', 'rocketscience'], catch_exceptions=False)

    assert isinstance(result.exception, SystemExit)
    assert 'No such command "rocketscience"' in result.output
    assert result.exit_code == 2
