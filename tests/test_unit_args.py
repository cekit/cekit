import pytest
import sys

from cekit.cli import Cekit


@pytest.mark.parametrize('command', ['generate', 'build', 'test'])
def test_args_command(mocker, command):
    mocker.patch.object(sys, 'argv', ['cekit', command])

    assert Cekit().parse().args.commands == [command]


def test_args_not_valid_command(mocker):
    mocker.patch.object(sys, 'argv', ['cekit', 'explode'])

    with pytest.raises(SystemExit):
        Cekit().parse()


@pytest.mark.parametrize('tags, build_tags, expected', [
    (['foo'], ['bar'], ['foo', 'bar']),
    ([], ['bar'], ['bar']),
    (['foo'], [], ['foo']),
    (['foo', 'bar'], ['baz', 'foe'], ['foo', 'bar', 'baz', 'foe'])])
def test_args_tags(mocker, tags, build_tags, expected):
    tags = sum([['--tag', t] for t in tags], [])
    build_tags = sum([['--build-tag', t] for t in build_tags], [])

    mocker.patch.object(sys, 'argv', ['cekit', 'generate'] + tags + build_tags)
    assert Cekit().parse().args.tags == expected


@pytest.mark.parametrize('engine', ['osbs', 'docker'])
def test_args_build_engine(mocker, engine):
    mocker.patch.object(sys, 'argv', ['cekit', 'build', '--build-engine', engine])

    assert Cekit().parse().args.build_engine == engine


def test_args_invalid_build_engine(mocker):
    mocker.patch.object(sys, 'argv', ['cekit', 'build', '--build-engine', 'rkt'])

    with pytest.raises(SystemExit):
        Cekit().parse()


def test_args_osbs_user(mocker):
    mocker.patch.object(sys, 'argv', ['cekit',
                                      'build',
                                      '--build-engine',
                                      'osbs',
                                      '--build-osbs-user',
                                      'USER'])

    assert Cekit().parse().args.build_osbs_user == 'USER'


def test_args_config_default(mocker):
    mocker.patch.object(sys, 'argv', ['cekit',
                                      'generate'])

    assert Cekit().parse().args.config == '~/.cekit'


def test_args_config(mocker):
    mocker.patch.object(sys, 'argv', ['cekit',
                                      '--config',
                                      'whatever',
                                      'generate'])

    assert Cekit().parse().args.config == 'whatever'


def test_args_osbs_nowait(mocker):
    mocker.patch.object(sys, 'argv', ['cekit',
                                      'build',
                                      '--build-osbs-nowait'])

    assert Cekit().parse().args.build_osbs_nowait is True


def test_args_osbs_no_nowait(mocker):
    mocker.patch.object(sys, 'argv', ['cekit',
                                      'build'])

    assert Cekit().parse().args.build_osbs_nowait is False
