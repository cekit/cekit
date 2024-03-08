import os
import re
import sys

import pytest
from click.testing import CliRunner

from cekit.cache.cli import cli
from cekit.crypto import SUPPORTED_HASH_ALGORITHMS


def test_cekit_cache_ls(tmpdir):
    work_dir = str(tmpdir.mkdir("work_dir"))

    result = run_cekit_cache(["-v", "--work-dir", work_dir, "ls"])

    assert "No artifacts cached!" in result.output


def test_cekit_cache_rm_non_existing(tmpdir):
    work_dir = str(tmpdir.mkdir("work_dir"))
    run_cekit_cache(["-v", "--work-dir", work_dir, "rm", "12345"], 1)


def test_cekit_cache_add_artifact(tmpdir):
    work_dir = str(tmpdir.mkdir("work_dir"))

    artifact = os.path.join(work_dir, "artifact")
    open(artifact, "a").close()

    result = run_cekit_cache(
        [
            "-v",
            "--work-dir",
            work_dir,
            "add",
            artifact,
            "--md5",
            "d41d8cd98f00b204e9800998ecf8427e",
        ]
    )

    assert "cached with UUID" in result.output

    # Artifact added to cache should have all supported checksums computed
    result = run_cekit_cache(["-v", "--work-dir", work_dir, "ls"])

    for alg in SUPPORTED_HASH_ALGORITHMS:
        assert alg in result.output

    assert (
        "sha512: cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e"
        in result.output
    )
    assert (
        "sha256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        in result.output
    )
    assert "sha1: da39a3ee5e6b4b0d3255bfef95601890afd80709" in result.output
    assert "md5: d41d8cd98f00b204e9800998ecf8427e" in result.output


def test_cekit_cache_add_artifact_existing(tmpdir):
    work_dir = str(tmpdir.mkdir("work_dir"))

    artifact = os.path.join(work_dir, "artifact")
    open(artifact, "a").close()

    args = [
        "-v",
        "--work-dir",
        work_dir,
        "add",
        artifact,
        "--md5",
        "d41d8cd98f00b204e9800998ecf8427e",
    ]

    run_cekit_cache(args)
    result = run_cekit_cache(args)

    assert "is already cached!" in result.output


def test_cekit_cache_delete_artifact(tmpdir):
    work_dir = str(tmpdir.mkdir("work_dir"))
    artifact = os.path.join(work_dir, "artifact")
    open(artifact, "a").close()

    result = run_cekit_cache(
        [
            "-v",
            "--work-dir",
            work_dir,
            "add",
            artifact,
            "--md5",
            "d41d8cd98f00b204e9800998ecf8427e",
        ]
    )

    artifact_uuid = re.search(r"\'(.*)\'$", result.output).group(1)

    run_cekit_cache(["-v", "--work-dir", work_dir, "rm", artifact_uuid])


def test_cekit_cache_delete_not_existing_artifact(tmpdir):
    work_dir = str(tmpdir.mkdir("work_dir"))

    result = run_cekit_cache(["-v", "--work-dir", work_dir, "rm", "foo"], 1)
    assert "Artifact with UUID 'foo' doesn't exists in the cache" in result.output


def test_cekit_cannot_add_artifact_without_checksum(tmpdir):
    work_dir = str(tmpdir.mkdir("work_dir"))
    artifact = os.path.join(work_dir, "artifact")
    open(artifact, "a").close()

    result = run_cekit_cache(["--work-dir", work_dir, "add", artifact], 2)

    assert "At least one checksum must be provided" in result.output


@pytest.mark.parametrize("algorithm", SUPPORTED_HASH_ALGORITHMS)
def test_cekit_supported_algorithms(tmpdir, algorithm):
    """
    This is a bit counter intuitive, but we try to cache an artifact
    with all known supported hash algorithms. In case when the algorithm
    would not be supported, it would result in return code 2 and a different error message
    """

    work_dir = str(tmpdir.mkdir("work_dir"))

    artifact = os.path.join(work_dir, "artifact")
    open(artifact, "a").close()

    result = run_cekit_cache(
        [
            "-v",
            "--work-dir",
            work_dir,
            "add",
            artifact,
            f"--{algorithm}",
            "WRONG!",
        ],
        1,
    )

    assert (
        f"Cannot cache artifact {artifact}: Artifact checksum verification failed!"
        in result.output
    )


def test_cekit_cache_clear(mocker, tmpdir):
    work_dir = str(tmpdir.mkdir("work_dir"))
    mock_rmtree = mocker.patch("shutil.rmtree")

    result = run_cekit_cache(["-v", "--work-dir", work_dir, "clear"], 0, "y\n")

    mock_rmtree.assert_called_once_with(os.path.join(work_dir, "cache"))
    assert "Artifact cache cleared!" in result.output


def test_cekit_cache_clear_no_confirm(mocker, tmpdir):
    work_dir = str(tmpdir.mkdir("work_dir"))
    mock_rmtree = mocker.patch("shutil.rmtree")

    result = run_cekit_cache(["-v", "--work-dir", work_dir, "clear"], 0, "n\n")

    mock_rmtree.assert_not_called()
    assert "Artifact cache cleared!" not in result.output


def test_cekit_cache_clear_no_confirm_by_default(mocker, tmpdir):
    work_dir = str(tmpdir.mkdir("work_dir"))
    mock_rmtree = mocker.patch("shutil.rmtree")

    result = run_cekit_cache(["-v", "--work-dir", work_dir, "clear"], 0, "\n")

    mock_rmtree.assert_not_called()
    assert "Artifact cache cleared!" not in result.output


def test_cekit_cache_clear_with_error(mocker, tmpdir):
    work_dir = str(tmpdir.mkdir("work_dir"))

    mocker.patch("shutil.rmtree", side_effect=Exception)

    result = run_cekit_cache(["-v", "--work-dir", work_dir, "clear"], 1, "y\n")

    assert (
        "An error occurred while removing the artifact cache directory '{}'".format(
            os.path.join(work_dir, "cache")
        )
        in result.output
    )


def run_cekit_cache(args, return_code=0, i=None):
    result = CliRunner().invoke(cli, args, input=i, catch_exceptions=False)
    sys.stdout.write("\n")
    sys.stdout.write(result.output)

    assert result.exit_code == return_code

    return result
