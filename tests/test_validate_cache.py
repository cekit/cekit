import os
import re
import pytest
import sys

from cekit.cache.cli import cli
from cekit.crypto import SUPPORTED_HASH_ALGORITHMS

from click.testing import CliRunner


def test_cekit_cache_ls(mocker, tmpdir):
    work_dir = str(tmpdir.mkdir('work_dir'))

    result = run_cekit_cache(['-v',
                              '--work-dir',
                              work_dir,
                              'ls'])

    assert 'No artifacts cached!' in result.output


def test_cekit_cache_rm_non_existing(mocker, tmpdir):
    work_dir = str(tmpdir.mkdir('work_dir'))
    run_cekit_cache(['-v',
                     '--work-dir',
                     work_dir,
                     'rm',
                     '12345'], 1)


def test_cekit_cache_add_artifact(mocker, tmpdir):
    work_dir = str(tmpdir.mkdir('work_dir'))

    artifact = os.path.join(work_dir, 'artifact')
    open(artifact, 'a').close()

    result = run_cekit_cache(['-v',
                              '--work-dir',
                              work_dir,
                              'add',
                              artifact,
                              '--md5',
                              'd41d8cd98f00b204e9800998ecf8427e'])

    assert "cached with UUID" in result.output


def test_cekit_cache_add_artifact_existing(mocker, tmpdir):
    work_dir = str(tmpdir.mkdir('work_dir'))

    artifact = os.path.join(work_dir, 'artifact')
    open(artifact, 'a').close()

    args = ['-v',
            '--work-dir',
            work_dir,
            'add',
            artifact,
            '--md5',
            'd41d8cd98f00b204e9800998ecf8427e']

    run_cekit_cache(args)
    result = run_cekit_cache(args)

    assert 'is already cached!' in result.output


def test_cekit_cache_delete_artifact(mocker, tmpdir):
    work_dir = str(tmpdir.mkdir('work_dir'))
    artifact = os.path.join(work_dir, 'artifact')
    open(artifact, 'a').close()

    result = run_cekit_cache(['-v',
                              '--work-dir',
                              work_dir,
                              'add',
                              artifact,
                              '--md5',
                              'd41d8cd98f00b204e9800998ecf8427e'])

    artifact_uuid = re.search(r'\'(.*)\'$', result.output).group(1)

    run_cekit_cache(['-v',
                     '--work-dir',
                     work_dir,
                     'rm',
                     artifact_uuid])


def test_cekit_cache_delete_not_existing_artifact(mocker, tmpdir):
    work_dir = str(tmpdir.mkdir('work_dir'))

    result = run_cekit_cache(['-v',
                              '--work-dir',
                              work_dir,
                              'rm',
                              'foo'], 1)
    assert "Artifact with UUID 'foo' doesn't exists in the cache" in result.output


def test_cekit_cannot_add_artifact_without_checksum(mocker, tmpdir):
    work_dir = str(tmpdir.mkdir('work_dir'))
    artifact = os.path.join(work_dir, 'artifact')
    open(artifact, 'a').close()

    result = run_cekit_cache(['--work-dir',
                              work_dir,
                              'add',
                              artifact], 2)

    assert "At least one checksum must be provided" in result.output


@pytest.mark.parametrize('algorithm', SUPPORTED_HASH_ALGORITHMS)
def test_cekit_supported_algorithms(mocker, tmpdir, algorithm):
    """
    This is a bit counter intuitive, but we try to cache an artifact
    with all known supported hash algorithms. In case when the algorithm
    would not be supported, it would result in return code 2 and a different error message
    """

    work_dir = str(tmpdir.mkdir('work_dir'))

    artifact = os.path.join(work_dir, 'artifact')
    open(artifact, 'a').close()

    result = run_cekit_cache(['-v',
                              '--work-dir',
                              work_dir,
                              'add',
                              artifact,
                              "--{}".format(algorithm),
                              'WRONG!'], 1)

    assert "Cannot cache artifact {}: Artifact checksum verification failed!".format(
        artifact) in result.output


def run_cekit_cache(args, rc=0):
    result = CliRunner().invoke(cli, args, catch_exceptions=False)
    assert result.exit_code == rc

    return result
