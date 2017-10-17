import pytest
import sys

from concreate.cli import Concreate


@pytest.mark.parametrize('command', ['generate', 'build', 'test'])
def test_args_command(mocker, command):
    mocker.patch.object(sys, 'argv', ['concreate', command])

    assert Concreate().parse().args.commands == [command]


def test_args_not_valid_command(mocker):
    mocker.patch.object(sys, 'argv', ['concreate', 'explode'])

    with pytest.raises(SystemExit):
        Concreate().parse()


@pytest.mark.parametrize('tags, build_tags, expected', [
    (['foo'], ['bar'], ['foo', 'bar']),
    ([], ['bar'], ['bar']),
    (['foo'], [], ['foo']),
    (['foo', 'bar'], ['baz', 'foe'], ['foo', 'bar', 'baz', 'foe'])])
def test_args_tags(mocker, tags, build_tags, expected):
    tags = sum([['--tag', t] for t in tags], [])
    build_tags = sum([['--build-tag', t] for t in build_tags], [])

    mocker.patch.object(sys, 'argv', ['concreate', 'generate'] + tags + build_tags)
    assert Concreate().parse().args.tags == expected


@pytest.mark.parametrize('engine', ['osbs', 'docker'])
def test_args_build_engine(mocker, engine):
    mocker.patch.object(sys, 'argv', ['concreate', 'build', '--build-engine', engine])

    assert Concreate().parse().args.build_engine == engine


def test_args_invalid_build_engine(mocker):
    mocker.patch.object(sys, 'argv', ['concreate', 'build', '--build-engine', 'rkt'])

    with pytest.raises(SystemExit):
        Concreate().parse()


