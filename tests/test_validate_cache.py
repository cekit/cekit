import os
import pytest
import sys

from cekit.cache.cli import CacheCli


def test_cekit_cache_ls(mocker, tmpdir, capsys):
    work_dir = str(tmpdir.mkdir('work_dir'))
    mocker.patch.object(sys, 'argv', ['cekit-cache',
                                      '--work-dir',
                                      work_dir,
                                      '-v',
                                      'ls'])
    run_cekit_cache()
    out, err = capsys.readouterr()
    assert 'No artifacts cached!' in out


def test_cekit_cache_rm_non_existing(mocker, tmpdir):
    work_dir = str(tmpdir.mkdir('work_dir'))
    mocker.patch.object(sys, 'argv', ['cekit-cache',
                                      '--work-dir',
                                      work_dir,
                                      '-v',
                                      'rm',
                                      '12345'])
    run_cekit_cache(1)


def test_cekit_cache_add_artifact(mocker, tmpdir, capsys):
    work_dir = str(tmpdir.mkdir('work_dir'))
    out, err = capsys.readouterr()

    artifact = os.path.join(work_dir, 'artifact')
    open(artifact, 'a').close()
    
    mocker.patch.object(sys, 'argv', ['cekit-cache',
                                      '--work-dir',
                                      work_dir,
                                      '-v',
                                      'add',
                                      artifact,
                                      '--md5',
                                      'd41d8cd98f00b204e9800998ecf8427e'])
    run_cekit_cache(0)


def test_cekit_cache_add_artifact_existing(mocker, tmpdir, capsys):
    work_dir = str(tmpdir.mkdir('work_dir'))

    artifact = os.path.join(work_dir, 'artifact')
    open(artifact, 'a').close()
    mocker.patch.object(sys, 'argv', ['cekit-cache',
                                      '--work-dir',
                                      work_dir,
                                      '-v',
                                      'add',
                                      artifact,
                                      '--md5',
                                      'd41d8cd98f00b204e9800998ecf8427e'])
    run_cekit_cache(0)
    run_cekit_cache(0)
    out, err = capsys.readouterr()
    assert 'Artifact is already cached!' in out


def test_cekit_cache_delete_artifact(mocker, tmpdir, capsys):
    work_dir = str(tmpdir.mkdir('work_dir'))

    artifact = os.path.join(work_dir, 'artifact')
    open(artifact, 'a').close()
    mocker.patch.object(sys, 'argv', ['cekit-cache',
                                      '--work-dir',
                                      work_dir,
                                      '-v',
                                      'add',
                                      artifact,
                                      '--md5',
                                      'd41d8cd98f00b204e9800998ecf8427e'])
    run_cekit_cache(0)
    out, err = capsys.readouterr()
    artifact_id = out[:-1]

    mocker.patch.object(sys, 'argv', ['cekit-cache',
                                      '--work-dir',
                                      work_dir,
                                      '-v',
                                      'rm',
                                      artifact_id])

    run_cekit_cache(0)


def test_cekit_cache_delete_not_existing_artifact(mocker, tmpdir, capsys):
    work_dir = str(tmpdir.mkdir('work_dir'))
    mocker.patch.object(sys, 'argv', ['cekit-cache',
                                      '--work-dir',
                                      work_dir,
                                      '-v',
                                      'rm',
                                      'foo'])

    run_cekit_cache(1)
    out, err = capsys.readouterr()
    assert "Artifact doesn't exists" in out


def test_cekit_cannot_add_artifact_without_checksum(mocker, tmpdir, capsys):
    work_dir = str(tmpdir.mkdir('work_dir'))

    artifact = os.path.join(work_dir, 'artifact')
    open(artifact, 'a').close()
    mocker.patch.object(sys, 'argv', ['cekit-cache',
                                      '--work-dir',
                                      work_dir,
                                      'add',
                                      artifact])

    run_cekit_cache(1)
    out, err = capsys.readouterr()
    assert "Cannot cache Artifact without checksum" in out


def run_cekit_cache(rc=0):
    with pytest.raises(SystemExit) as system_exit:
        CacheCli().parse().run()
    assert system_exit.value.code == rc
