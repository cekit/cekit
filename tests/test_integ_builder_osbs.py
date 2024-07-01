# -*- encoding: utf-8 -*-
import contextlib
import copy
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
from enum import Enum, auto

import pytest
import yaml
from click.testing import CliRunner, Result
from mock.mock import Mock, call

from cekit.cli import cli
from cekit.tools import Chdir
from cekit.version import __version__

image_descriptor = {
    "schema_version": 1,
    "from": "centos:7",
    "name": "test/image",
    "version": "1.0",
    "labels": [{"name": "foo", "value": "bar"}, {"name": "labela", "value": "a"}],
    "osbs": {"repository": {"name": "repo", "branch": "branch"}},
}


def run_cekit(
    cwd, parameters=["build", "--dry-run", "docker"], message=None, return_code=0
) -> Result:
    with Chdir(cwd):
        result = CliRunner().invoke(cli, parameters, catch_exceptions=False)
        sys.stdout.write("\n")
        sys.stdout.write(result.output)

        assert result.exit_code == return_code

        if message:
            assert message in result.output

        return result


class OSBSTestFlags(Enum):
    NONE = auto()
    MULTI_ADD = auto()
    TRIGGER_GIT_FAILURE = auto()
    NO_SKIP_COMMITTING = auto()
    RM_FETCH_FILE = auto()


def run_osbs(
    descriptor,
    image_dir,
    mocker,
    return_code=0,
    build_command=None,
    general_command=None,
    flag: OSBSTestFlags = OSBSTestFlags.NONE,
) -> Mock:
    if build_command is None:
        build_command = ["build", "osbs"]

    if general_command is None:
        general_command = ["--redhat"]

    if flag == OSBSTestFlags.NO_SKIP_COMMITTING:
        skip_committing = False
    else:
        skip_committing = True

    # We are mocking it, so do not require it at test time
    mocker.patch("cekit.builders.osbs.OSBSBuilder.dependencies", return_value={})
    mocker.patch("cekit.builders.osbs.OSBSBuilder._wait_for_osbs_task")
    mocker.patch("cekit.builders.osbs.Git.prepare")

    side_affect = [
        subprocess.CompletedProcess(
            "", 0, "true"
        ),  # git rev-parse --is-inside-work-tree
        subprocess.CompletedProcess(
            "", 0, "/home/repos/path"
        ),  # git rev-parse --show-toplevel
        subprocess.CompletedProcess("", 0, "branch"),  # git rev-parse --abbrev-ref HEAD
        subprocess.CompletedProcess(
            "", 0, "3b9283cb26b35511517ff5c0c3e11f490cba8feb"
        ),  # git rev-parse HEAD
        subprocess.CompletedProcess("ls-files", 0, ""),  # git ls-files .
    ]
    if flag == OSBSTestFlags.RM_FETCH_FILE:
        side_affect.append(subprocess.CompletedProcess("rm", 0, ""))

    # Required for all tests up to test_osbs_builder_with_fetch_artifacts_url_file_creation_1
    side_affect.append(
        subprocess.CompletedProcess("add", 0, "")
    )  # git add --all [Optional]

    if flag == OSBSTestFlags.MULTI_ADD:
        side_affect.append(subprocess.CompletedProcess("add", 0, ""))

    side_affect.extend(
        [
            subprocess.CompletedProcess(
                "diff-index", int(skip_committing), ""
            ),  # git diff-index --quiet --cached
            subprocess.CompletedProcess("commit", 0, ""),
            subprocess.CompletedProcess(
                "", 0, ""
            ),  # git ls-files --others --exclude-standard
            subprocess.CompletedProcess(
                "diff-files", 0, ""
            ),  # git diff-files --name-only
        ]
    )
    if flag == OSBSTestFlags.TRIGGER_GIT_FAILURE:
        side_affect.append(
            subprocess.CalledProcessError(1, "git", output="A GIT ERROR")
        )
    else:
        side_affect.append(subprocess.CompletedProcess("push", 0, ""))  # git push -q

    side_affect.extend(
        [
            subprocess.CompletedProcess("", 0, ""),  # git status
            subprocess.CompletedProcess("", 0, ""),  # git show
            subprocess.CompletedProcess(
                "", 0, "ssh://someuser@somehost.com/containers/somerepo"
            ),  # git config --get remote.origin.url
            subprocess.CompletedProcess(
                "", 0, "3b9283cb26b35511517ff5c0c3e11f490cba8feb"
            ),  # git rev-parse HEAD
            subprocess.CompletedProcess("", 0, "1234"),  # brew call --python...
            # For git tagging
            subprocess.CompletedProcess(
                "", 0, """{"koji_builds": ["123456"]}"""
            ),  # getTaskResult
            subprocess.CompletedProcess(
                "", 0, """{"nvr": "org.foo-foobar-1.0-1"}"""
            ),  # getBuild
            subprocess.CompletedProcess("", 0, ""),  # git tag [Optional]
            subprocess.CompletedProcess("", 0, ""),  # git push [Optional]
            subprocess.CompletedProcess(
                "", 0, "https://my.cekit.repo/foo"
            ),  # git config [Optional]
            subprocess.CompletedProcess("", 0, ""),  # git tag [Optional]
            subprocess.CompletedProcess("", 0, ""),  # git push [Optional]
        ]
    )

    patched_run = mocker.patch.object(subprocess, "run", side_effect=side_affect)

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(descriptor, fd, default_flow_style=False)

    run_cekit(
        image_dir,
        general_command
        + ["-v", "--work-dir", image_dir, "--config", "config"]
        + build_command,
        return_code=return_code,
    )

    # Complete hack, but I can't get the side_effect to return CompletedProcess _and_ execute this rm.
    if flag == OSBSTestFlags.RM_FETCH_FILE:
        with contextlib.suppress(FileNotFoundError):
            os.remove(
                os.path.join(image_dir, "osbs", "repo", "fetch-artifacts-url.yaml")
            )
        with contextlib.suppress(FileNotFoundError):
            os.remove(
                os.path.join(image_dir, "osbs", "repo", "fetch-artifacts-pnc.yaml")
            )

    return patched_run


def test_osbs_builder_with_assume_yes(tmpdir, mocker, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

    # Specifically set the decision result to False, to fail any build
    # that depends on the decision. But in case the --assume-yes switch is used
    # we should not get to this point at all. If we get, the test should fail.
    mock_decision = mocker.patch("cekit.tools.decision", return_value=False)

    source_dir = tmpdir.mkdir("source")
    source_dir.mkdir("osbs").mkdir("repo")

    mock_run = run_osbs(
        copy.deepcopy(image_descriptor),
        str(source_dir),
        mocker,
        0,
        ["build", "osbs", "--assume-yes"],
    )

    mock_decision.assert_not_called()

    # DEBUG:
    # print(f"#### run got {mock_run.mock_calls}")
    # print(caplog.text)

    mock_run.assert_has_calls(
        [
            call(
                ["git", "add", "--all", "Dockerfile"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
            call(
                ["git", "push", "-q", "origin", "branch"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
            call(
                [
                    "git",
                    "commit",
                    "-q",
                    "-m",
                    "Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb",
                ],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
        ],
        any_order=True,
    )

    assert (
        "Committing with message: 'Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb'"
        in caplog.text
    )
    assert "Image was built successfully in OSBS!" in caplog.text


def test_osbs_builder_with_process_error(tmpdir, mocker, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

    # Specifically set the decision result to False, to fail any build
    # that depends on the decision. But in case the --assume-yes switch is used
    # we should not get to this point at all. If we get, the test should fail.
    mock_decision = mocker.patch("cekit.tools.decision", return_value=False)

    source_dir = tmpdir.mkdir("source")
    source_dir.mkdir("osbs").mkdir("repo")

    run_osbs(
        copy.deepcopy(image_descriptor),
        str(source_dir),
        mocker,
        1,
        ["build", "osbs", "--assume-yes"],
        flag=OSBSTestFlags.TRIGGER_GIT_FAILURE,
    )

    mock_decision.assert_not_called()

    assert "A GIT ERROR" in caplog.text
    assert "Image was built successfully in OSBS!" not in caplog.text


def test_osbs_builder_with_push_with_sync_only(tmpdir, mocker, caplog):
    """
    Should sync with dist-git repository without kicking the build
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    source_dir = tmpdir.mkdir("source")
    repo_dir = source_dir.mkdir("osbs").mkdir("repo")

    mocker.patch("cekit.tools.decision", return_value=True)

    descriptor = copy.deepcopy(image_descriptor)

    mock_run = run_osbs(
        descriptor, str(source_dir), mocker, 0, ["build", "osbs", "--sync-only"]
    )

    assert os.path.exists(str(repo_dir.join("Dockerfile"))) is True

    mock_run.assert_has_calls(
        [
            mocker.call(
                ["git", "add", "--all", "Dockerfile"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
            call(
                ["git", "push", "-q", "origin", "branch"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
            mocker.call(
                [
                    "git",
                    "commit",
                    "-q",
                    "-m",
                    "Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb",
                ],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
        ],
        any_order=True,
    )

    assert (
        "Committing with message: 'Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb'"
        in caplog.text
    )
    assert (
        "The --sync-only parameter was specified, build will not be executed, exiting"
        in caplog.text
    )


def test_osbs_builder_kick_build_without_push(tmpdir, mocker, caplog):
    """
    Does not push sources to dist-git. This is the case when the
    generated files are the same as already existing in dist-git
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("cekit.tools.decision", return_value=True)

    source_dir = tmpdir.mkdir("source")
    repo_dir = source_dir.mkdir("osbs").mkdir("repo")

    descriptor = copy.deepcopy(image_descriptor)

    mock_run = run_osbs(
        descriptor, str(source_dir), mocker, flag=OSBSTestFlags.NO_SKIP_COMMITTING
    )

    assert os.path.exists(str(repo_dir.join("Dockerfile"))) is True

    mock_run.assert_has_calls(
        [
            mocker.call(
                ["git", "add", "--all", "Dockerfile"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            )
        ]
    )

    assert "No changes made to the code, committing skipped" in caplog.text
    assert "Image was built successfully in OSBS!" in caplog.text


def test_osbs_builder_kick_build_with_push(tmpdir, mocker, caplog):
    """
    Does push sources to dist-git.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    source_dir = tmpdir.mkdir("source")
    repo_dir = source_dir.mkdir("osbs").mkdir("repo")

    mocker.patch("cekit.tools.decision", return_value=True)

    descriptor = copy.deepcopy(image_descriptor)

    mock_run = run_osbs(descriptor, str(source_dir), mocker)

    assert os.path.exists(str(repo_dir.join("Dockerfile"))) is True

    mock_run.assert_has_calls(
        [
            mocker.call(
                ["git", "add", "--all", "Dockerfile"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
            mocker.call(
                ["git", "push", "-q", "origin", "branch"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
            mocker.call(
                [
                    "git",
                    "commit",
                    "-q",
                    "-m",
                    "Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb",
                ],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
        ],
        any_order=True,
    )

    assert (
        "Committing with message: 'Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb'"
        in caplog.text
    )
    assert "Image was built successfully in OSBS!" in caplog.text


# https://github.com/cekit/cekit/issues/504
def test_osbs_builder_add_help_file(tmpdir, mocker, caplog):
    """
    Checks if help.md file is generated and added to dist-git
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("cekit.tools.decision", return_value=True)

    source_dir = tmpdir.mkdir("source")
    repo_dir = source_dir.mkdir("osbs").mkdir("repo")

    descriptor = copy.deepcopy(image_descriptor)
    descriptor["help"] = {"add": True}

    mock_run = run_osbs(
        descriptor, str(source_dir), mocker, flag=OSBSTestFlags.NO_SKIP_COMMITTING
    )

    assert os.path.exists(str(repo_dir.join("Dockerfile"))) is True
    assert os.path.exists(str(repo_dir.join("help.md"))) is True

    mock_run.assert_has_calls(
        [
            mocker.call(
                ["git", "add", "--all", "Dockerfile"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
            mocker.call(
                ["git", "add", "--all", "help.md"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
        ]
    )
    assert len(mock_run.mock_calls) == 11
    assert "Image was built successfully in OSBS!" in caplog.text


# https://github.com/cekit/cekit/issues/394
def test_osbs_builder_add_extra_files(tmpdir, mocker, caplog):
    """
    Checks if content of the 'osbs_extra' directory content is copied to dist-git
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("cekit.tools.decision", return_value=True)

    source_dir = tmpdir.mkdir("source")
    repo_dir = source_dir.mkdir("osbs").mkdir("repo")
    dist_dir = source_dir.mkdir("osbs_extra")

    dist_dir.join("file_a").write_text("Some content", "utf-8")
    dist_dir.join("file_b").write_text("Some content", "utf-8")
    dist_dir.mkdir("child").join("other").write_text("Some content", "utf-8")

    os.symlink("/etc", str(dist_dir.join("a_symlink")))

    mock_run = run_osbs(
        image_descriptor, str(source_dir), mocker, flag=OSBSTestFlags.NO_SKIP_COMMITTING
    )

    assert os.path.exists(str(repo_dir.join("Dockerfile"))) is True
    assert os.path.exists(str(repo_dir.join("osbs_extra", "file_a"))) is True
    assert os.path.exists(str(repo_dir.join("osbs_extra", "file_b"))) is True

    assert (
        call(
            ["git", "add", "--all", "Dockerfile"],
            stderr=None,
            stdout=None,
            check=True,
            universal_newlines=True,
        )
        in mock_run.mock_calls
    )
    assert (
        call(
            ["git", "add", "--all", "osbs_extra"],
            stderr=None,
            stdout=None,
            check=True,
            universal_newlines=True,
        )
        in mock_run.mock_calls
    )

    assert os.path.exists(str(repo_dir.join("osbs_extra", "file_b"))) is True
    assert len(mock_run.mock_calls) == 11
    assert "Image was built successfully in OSBS!" in caplog.text
    assert f"Copying files to dist-git '{str(repo_dir)}' directory" in caplog.text
    assert (
        "Copying 'target/image/osbs_extra' to '{}'...".format(
            os.path.join(str(repo_dir), "osbs_extra")
        )
        in caplog.text
    )
    assert "Staging 'osbs_extra'..." in caplog.text


def test_osbs_builder_add_extra_files_with_extra_dir_target(tmpdir, mocker, caplog):
    """
    Checks if content of the 'osbs_extra' directory content is copied to dist-git and embedded in Dockerfile
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("cekit.tools.decision", return_value=True)

    source_dir = tmpdir.mkdir("source")
    repo_dir = source_dir.mkdir("osbs").mkdir("repo")
    dist_dir = source_dir.mkdir("osbs_extra")
    repo_dir_osbs_extra = repo_dir.mkdir("osbs_extra")
    repo_dir_osbs_extra.mkdir("foobar_original")
    repo_dir_osbs_extra.join("config_original.yaml").write_text("Some content", "utf-8")

    dist_dir.join("file_a").write_text("Some content", "utf-8")
    dist_dir.join("file_b").write_text("Some content", "utf-8")
    dist_dir.mkdir("child").join("other").write_text("Some content", "utf-8")

    os.symlink("/etc", str(dist_dir.join("a_symlink")))

    overrides_descriptor = {
        "schema_version": 1,
        "osbs": {"extra_dir_target": "/foobar"},
    }

    with open(os.path.join(str(source_dir), "overrides.yaml"), "w") as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    mock_run = run_osbs(
        image_descriptor,
        str(source_dir),
        mocker,
        build_command=["build", "--overrides-file", "overrides.yaml", "osbs"],
        flag=OSBSTestFlags.NO_SKIP_COMMITTING,
    )

    assert os.path.exists(str(repo_dir.join("Dockerfile"))) is True
    assert os.path.exists(str(repo_dir.join("osbs_extra").join("file_a"))) is True
    assert os.path.exists(str(repo_dir.join("osbs_extra").join("file_b"))) is True

    assert (
        mocker.call(
            ["git", "rm", "-rf", "osbs_extra"],
            stderr=None,
            stdout=None,
            check=True,
            universal_newlines=True,
        )
        in mock_run.mock_calls
    )
    assert (
        mocker.call(
            ["git", "add", "--all", "osbs_extra"],
            stderr=None,
            stdout=None,
            check=True,
            universal_newlines=True,
        )
        in mock_run.mock_calls
    )
    assert (
        mocker.call(
            ["git", "add", "--all", "osbs_extra"],
            stderr=None,
            stdout=None,
            check=True,
            universal_newlines=True,
        )
        in mock_run.mock_calls
    )

    assert os.path.exists(str(repo_dir.join("osbs_extra").join("file_b"))) is True
    assert len(mock_run.mock_calls) == 12
    assert "Image was built successfully in OSBS!" in caplog.text
    assert f"Copying files to dist-git '{str(repo_dir)}' directory" in caplog.text
    assert "Removing old osbs extra directory : osbs_extra" in caplog.text
    assert (
        "Copying 'target/image/osbs_extra' to '{}'...".format(
            os.path.join(str(repo_dir), "osbs_extra")
        )
        in caplog.text
    )
    assert "Staging 'osbs_extra'..." in caplog.text
    with open(os.path.join(str(repo_dir), "Dockerfile"), "r") as _file:
        dockerfile = _file.read()
        assert (
            """## START target image test/image:1.0
## \\
    FROM centos:7

    COPY osbs_extra /foobar

    USER root
"""
            in dockerfile
        )

    assert "COPY osbs_extra /foobar" in dockerfile


def test_osbs_builder_add_extra_files_non_default_with_extra_dir_target(
    tmpdir, mocker, caplog
):
    """
    Checks if content of the 'osbs_extra' directory content is copied to dist-git and embedded in Dockerfile
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("cekit.tools.decision", return_value=True)

    source_dir = tmpdir.mkdir("source")
    repo_dir = source_dir.mkdir("osbs").mkdir("repo")
    dist_dir = source_dir.mkdir("foobar")
    repo_dir.mkdir("foobar")

    dist_dir.join("file_a").write_text("Some content", "utf-8")
    dist_dir.join("file_b").write_text("Some content", "utf-8")
    dist_dir.mkdir("child").join("other").write_text("Some content", "utf-8")

    os.symlink("/etc", str(dist_dir.join("a_symlink")))

    overrides_descriptor = {
        "schema_version": 1,
        "osbs": {"extra_dir_target": "/", "extra_dir": "foobar"},
    }

    with open(os.path.join(str(source_dir), "overrides.yaml"), "w") as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    mock_run = run_osbs(
        image_descriptor,
        str(source_dir),
        mocker,
        build_command=["build", "--overrides-file", "overrides.yaml", "osbs"],
    )

    assert os.path.exists(str(repo_dir.join("Dockerfile"))) is True
    assert os.path.exists(str(repo_dir.join("foobar").join("file_a"))) is True
    assert os.path.exists(str(repo_dir.join("foobar").join("file_b"))) is True

    assert (
        mocker.call(
            ["git", "rm", "-rf", "foobar"],
            stderr=None,
            stdout=None,
            check=True,
            universal_newlines=True,
        )
        in mock_run.mock_calls
    )
    assert (
        mocker.call(
            ["git", "add", "--all", "foobar"],
            stderr=None,
            stdout=None,
            check=True,
            universal_newlines=True,
        )
        in mock_run.mock_calls
    )
    assert (
        mocker.call(
            ["git", "add", "--all", "Dockerfile"],
            stderr=None,
            stdout=None,
            check=True,
            universal_newlines=True,
        )
        in mock_run.mock_calls
    )

    assert os.path.exists(str(repo_dir.join("foobar").join("file_b"))) is True
    assert len(mock_run.mock_calls) == 12
    assert "Image was built successfully in OSBS!" in caplog.text
    assert f"Copying files to dist-git '{str(repo_dir)}' directory" in caplog.text
    assert "Removing old osbs extra directory : foobar" in caplog.text
    assert (
        f"Copying 'target/image/foobar' to '{os.path.join(str(repo_dir), 'foobar')}'..."
        in caplog.text
    )
    assert "Staging 'foobar'..." in caplog.text
    with open(os.path.join(str(repo_dir), "Dockerfile"), "r") as _file:
        dockerfile = _file.read()

    assert "COPY foobar /" in dockerfile


def test_osbs_builder_add_extra_files_and_overwrite(tmpdir, mocker, caplog):
    """
    Checks if content of the 'osbs_extra' directory content is copied to dist-git
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("cekit.tools.decision", return_value=True)

    source_dir = tmpdir.mkdir("source")
    repo_dir = source_dir.mkdir("osbs").mkdir("repo")
    repo_dir.mkdir("osbs_extra").mkdir("child").join("other").write_text(
        "Some content", "utf-8"
    )

    dist_dir = source_dir.mkdir("osbs_extra")

    dist_dir.join("file_a").write_text("Some content", "utf-8")
    dist_dir.join("file_b").write_text("Some content", "utf-8")
    dist_dir.mkdir("child").join("other").write_text("Some content", "utf-8")

    os.symlink("/etc", str(dist_dir.join("a_symlink")))

    mock_run = run_osbs(image_descriptor, str(source_dir), mocker)

    assert os.path.exists(str(repo_dir.join("Dockerfile"))) is True
    assert os.path.exists(str(repo_dir.join("osbs_extra", "file_a"))) is True
    assert os.path.exists(str(repo_dir.join("osbs_extra", "file_b"))) is True
    assert os.path.exists(str(repo_dir.join("osbs_extra", "child"))) is True
    assert os.path.exists(str(repo_dir.join("osbs_extra", "child", "other"))) is True

    assert (
        mocker.call(
            ["git", "rm", "-rf", "osbs_extra"],
            stderr=None,
            stdout=None,
            check=True,
            universal_newlines=True,
        )
        in mock_run.mock_calls
    )
    assert (
        mocker.call(
            ["git", "add", "--all", "osbs_extra"],
            stderr=None,
            stdout=None,
            check=True,
            universal_newlines=True,
        )
        in mock_run.mock_calls
    )
    assert (
        mocker.call(
            ["git", "add", "--all", "Dockerfile"],
            stderr=None,
            stdout=None,
            check=True,
            universal_newlines=True,
        )
        in mock_run.mock_calls
    )

    assert len(mock_run.mock_calls) == 12
    assert "Image was built successfully in OSBS!" in caplog.text
    assert f"Copying files to dist-git '{str(repo_dir)}' directory" in caplog.text
    assert (
        "Copying 'target/image/osbs_extra' to '{}'...".format(
            os.path.join(str(repo_dir), "osbs_extra")
        )
        in caplog.text
    )
    assert "Staging 'osbs_extra'..." in caplog.text


# https://github.com/cekit/cekit/issues/394
def test_osbs_builder_add_extra_files_from_custom_dir(tmpdir, mocker, caplog):
    """
    Checks if content of the custom specified 'dist' directory content is copied to dist-git
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("cekit.tools.decision", return_value=True)

    source_dir = tmpdir.mkdir("source")
    repo_dir = source_dir.mkdir("osbs").mkdir("repo")
    dist_dir = source_dir.mkdir("dist")

    dist_dir.join("file_a").write_text("Some content", "utf-8")
    dist_dir.join("file_b").write_text("Some content", "utf-8")
    dist_dir.mkdir("child").join("other").write_text("Some content", "utf-8")

    os.symlink("/etc", str(dist_dir.join("a_symlink")))

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["osbs"]["extra_dir"] = "dist"

    mock_run = run_osbs(descriptor, str(source_dir), mocker)

    assert os.path.exists(str(repo_dir.join("Dockerfile"))) is True
    assert os.path.exists(str(repo_dir.join("dist").join("file_a"))) is True
    assert os.path.exists(str(repo_dir.join("dist").join("file_b"))) is True

    assert (
        mocker.call(
            ["git", "add", "--all", "dist"],
            stderr=None,
            stdout=None,
            check=True,
            universal_newlines=True,
        )
        in mock_run.mock_calls
    )
    assert (
        mocker.call(
            ["git", "add", "--all", "Dockerfile"],
            stderr=None,
            stdout=None,
            check=True,
            universal_newlines=True,
        )
        in mock_run.mock_calls
    )
    assert len(mock_run.mock_calls) == 11
    assert "Image was built successfully in OSBS!" in caplog.text
    assert f"Copying files to dist-git '{str(repo_dir)}' directory" in caplog.text
    assert (
        f"Copying 'target/image/dist' to '{os.path.join(str(repo_dir), 'dist')}'..."
        in caplog.text
    )
    assert "Staging 'dist'..." in caplog.text
    with open(os.path.join(str(repo_dir), "Dockerfile"), "r") as _file:
        dockerfile = _file.read()

    assert "COPY foobar /" not in dockerfile


# https://github.com/cekit/cekit/issues/542
def test_osbs_builder_extra_default(tmpdir, mocker, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

    source_dir = tmpdir.mkdir("source")

    shutil.copytree(
        os.path.join(os.path.dirname(__file__), "modules"),
        os.path.join(str(source_dir), "tests", "modules"),
    )

    descriptor = copy.deepcopy(image_descriptor)

    del descriptor["osbs"]

    run_osbs(descriptor, str(source_dir), mocker, return_code=1)

    with open(os.path.join(str(source_dir), "target", "image.yaml"), "r") as _file:
        effective = yaml.safe_load(_file)

    assert effective["osbs"] is not None
    assert effective["osbs"]["extra_dir"] == "osbs_extra"


def test_osbs_builder_add_files_to_dist_git_when_it_is_a_directory(
    tmpdir, mocker, caplog
):
    mocker.patch("cekit.tools.decision", return_value=True)

    res = mocker.Mock()
    res.getcode.return_value = 200
    res.read.side_effect = [b"test", None]

    mocker.patch("cekit.tools.urlopen", return_value=res)

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["artifacts"] = [{"path": "manifests", "dest": "/manifests"}]

    tmpdir.mkdir("osbs").mkdir("repo").mkdir(".git").join("other").write_text(
        "Some content", "utf-8"
    )

    tmpdir.mkdir("manifests")

    with open(
        os.path.join(str(tmpdir), "manifests", "some-manifest-file.yaml"), "w"
    ) as _file:
        _file.write("CONTENT")

    mock_run = run_osbs(descriptor, str(tmpdir), mocker, flag=OSBSTestFlags.MULTI_ADD)

    mock_run.assert_has_calls(
        [
            mocker.call(
                ["git", "add", "--all", "manifests"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
            mocker.call(
                ["git", "add", "--all", "Dockerfile"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
            call(
                ["git", "push", "-q", "origin", "branch"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
            call(
                [
                    "git",
                    "commit",
                    "-q",
                    "-m",
                    "Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb",
                ],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
        ],
        any_order=True,
    )
    assert "Skipping '.git' directory" in caplog.text
    assert "Staging 'manifests'..." in caplog.text


def test_osbs_builder_add_artifact_directory_to_dist_git_when_it_already_exists(
    tmpdir, mocker, caplog
):
    mocker.patch("cekit.tools.decision", return_value=True)

    res = mocker.Mock()
    res.getcode.return_value = 200
    res.read.side_effect = [b"test", None]

    mocker.patch("cekit.tools.urlopen", return_value=res)

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["artifacts"] = [{"path": "manifests", "dest": "/manifests"}]

    tmpdir.mkdir("osbs").mkdir("repo").mkdir(".git").join("other").write_text(
        "Some content", "utf-8"
    )

    tmpdir.join("osbs").join("repo").mkdir("manifests").join(
        "old-manifests.yaml"
    ).write_text("Some content", "utf-8")

    tmpdir.mkdir("manifests")

    with open(
        os.path.join(str(tmpdir), "manifests", "some-manifest-file.yaml"), "w"
    ) as _file:
        _file.write("CONTENT")

    mock_run = run_osbs(descriptor, str(tmpdir), mocker, flag=OSBSTestFlags.MULTI_ADD)

    mock_run.assert_has_calls(
        [
            mocker.call(
                ["git", "add", "--all", "manifests"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
            mocker.call(
                ["git", "add", "--all", "Dockerfile"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
            call(
                ["git", "push", "-q", "origin", "branch"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
            call(
                [
                    "git",
                    "commit",
                    "-q",
                    "-m",
                    "Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb",
                ],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
        ],
        any_order=True,
    )
    assert "Skipping '.git' directory" in caplog.text
    assert "Staging 'manifests'..." in caplog.text
    assert "Removing old 'manifests' directory" in caplog.text


def test_osbs_builder_add_files_to_dist_git_without_dotgit_directory(
    tmpdir, mocker, caplog
):
    mocker.patch("cekit.tools.decision", return_value=True)
    caplog.set_level(logging.DEBUG, logger="cekit")

    res = mocker.Mock()
    res.getcode.return_value = 200
    res.read.side_effect = [b"test", None]
    res.getheader.return_value = 0

    mocker.patch("cekit.tools.urlopen", return_value=res)

    (
        tmpdir.mkdir("osbs")
        .mkdir("repo")
        .mkdir(".git")
        .join("other")
        .write_text("Some content", "utf-8")
    )

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["artifacts"] = [{"url": "https://foo/bar.jar"}]

    mock_run = run_osbs(descriptor, str(tmpdir), mocker, flag=OSBSTestFlags.MULTI_ADD)

    mock_run.assert_has_calls(
        [
            mocker.call(
                ["git", "add", "--all", "fetch-artifacts-url.yaml"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
            mocker.call(
                ["git", "add", "--all", "Dockerfile"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
            call(
                ["git", "push", "-q", "origin", "branch"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
            mocker.call(
                [
                    "git",
                    "commit",
                    "-q",
                    "-m",
                    "Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb",
                ],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
        ],
        any_order=True,
    )
    assert "Skipping '.git' directory" in caplog.text
    with open(
        os.path.join(str(tmpdir), "target", "image", "fetch-artifacts-url.yaml"), "r"
    ) as _file:
        fetch_artifacts = yaml.safe_load(_file)
    assert len(fetch_artifacts) == 1
    assert fetch_artifacts[0] == {
        "md5": "098f6bcd4621d373cade4e832627b4f6",
        "target": "bar.jar",
        "url": "https://foo/bar.jar",
    }
    assert (
        "Artifact 'bar.jar' (as URL) added to fetch-artifacts-url.yaml" in caplog.text
    )


def test_osbs_builder_with_koji_target_based_on_branch(tmpdir, mocker, caplog):
    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.tools.urlopen")

    tmpdir.mkdir("osbs").mkdir("repo").mkdir(".git").join("other").write_text(
        "Some content", "utf-8"
    )

    descriptor = copy.deepcopy(image_descriptor)

    run_osbs(descriptor, str(tmpdir), mocker)

    assert (
        "About to execute 'brew call --python buildContainer --kwargs {'src': 'git+https://somehost.com/git/containers/somerepo#3b9283cb26b35511517ff5c0c3e11f490cba8feb', 'target': 'branch-containers-candidate', 'opts': {'scratch': True, 'git_branch': 'branch', 'yum_repourls': []}}'."
        in caplog.text
    )


def test_osbs_builder_with_koji_target_in_descriptor(tmpdir, mocker, caplog):
    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.tools.urlopen")

    tmpdir.mkdir("osbs").mkdir("repo").mkdir(".git").join("other").write_text(
        "Some content", "utf-8"
    )

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["osbs"]["koji_target"] = "some-target"

    run_osbs(descriptor, str(tmpdir), mocker)

    assert (
        "About to execute 'brew call --python buildContainer --kwargs {'src': 'git+https://somehost.com/git/containers/somerepo#3b9283cb26b35511517ff5c0c3e11f490cba8feb', 'target': 'some-target', 'opts': {'scratch': True, 'git_branch': 'branch', 'yum_repourls': []}}'."
        in caplog.text
    )


def test_osbs_builder_with_fetch_artifacts_plain_file_creation(tmpdir, mocker, caplog):
    """
    Checks whether the fetch-artifacts-url.yaml file is generated with plain artifact.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.tools.urlopen")
    mocker.patch(
        "cekit.generator.osbs.get_brew_url", return_value="http://random.url/path"
    )
    mocker.patch("cekit.builders.osbs.Git.push")

    tmpdir.mkdir("osbs").mkdir("repo")

    tmpdir.join("osbs").join("repo").join("fetch-artifacts-url.yaml").write_text(
        "Some content", "utf-8"
    )

    with Chdir(os.path.join(str(tmpdir), "osbs", "repo")):
        subprocess.run(["git", "init"])
        subprocess.run(["git", "add", "fetch-artifacts-url.yaml"])
        subprocess.run(["git", "commit", "-m", "Dummy"])

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["artifacts"] = [{"name": "artifact_name", "md5": "123456"}]

    run_osbs(descriptor, str(tmpdir), mocker)

    with open(
        os.path.join(str(tmpdir), "target", "image", "fetch-artifacts-url.yaml"), "r"
    ) as _file:
        fetch_artifacts = yaml.safe_load(_file)

    assert len(fetch_artifacts) == 1
    assert fetch_artifacts[0] == {
        "md5": "123456",
        "target": "artifact_name",
        "url": "http://random.url/path",
    }

    assert (
        "Artifact 'artifact_name' (as plain) added to fetch-artifacts-url.yaml"
        in caplog.text
    )


@pytest.mark.parametrize("flag", [[], ["--redhat"]])
def test_osbs_builder_with_fetch_artifacts_url_file_creation_1(
    tmpdir, mocker, caplog, flag
):
    """
    Checks whether the fetch-artifacts-url.yaml file is generated with URL artifact with md5 checksum.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.tools.urlopen")
    mocker.patch("cekit.builders.osbs.Git.push")

    tmpdir.mkdir("osbs").mkdir("repo")

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["artifacts"] = [
        {
            "name": "artifact_name",
            "md5": "123456",
            "url": "https://foo/bar.jar",
            "description": "http://foo.com/123456",
        }
    ]

    run_osbs(descriptor, str(tmpdir), mocker, general_command=flag)

    fau = os.path.join(str(tmpdir), "target", "image", "fetch-artifacts-url.yaml")
    with open(fau, "r") as _file:
        fetch_artifacts = yaml.safe_load(_file)

    assert len(fetch_artifacts) == 1
    assert fetch_artifacts[0] == {
        "md5": "123456",
        "target": "artifact_name",
        "url": "https://foo/bar.jar",
    }
    if len(flag):
        with open(fau) as myfile:
            assert "https://foo/bar.jar # http://foo.com/123456" in myfile.read()

    assert (
        "Artifact 'artifact_name' (as URL) added to fetch-artifacts-url.yaml"
        in caplog.text
    )


def test_osbs_builder_with_fetch_artifacts_url_file_creation_2(tmpdir, mocker, caplog):
    """
    Checks whether the fetch-artifacts-url.yaml file is generated with URL artifact with sha1 checksum.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.tools.urlopen")
    mocker.patch("cekit.builders.osbs.Git.push")

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["artifacts"] = [
        {"name": "artifact_name", "sha1": "123456", "url": "https://foo/bar.jar"}
    ]

    tmpdir.mkdir("osbs").mkdir("repo")

    run_osbs(descriptor, str(tmpdir), mocker)

    with open(
        os.path.join(str(tmpdir), "target", "image", "fetch-artifacts-url.yaml"), "r"
    ) as _file:
        fetch_artifacts = yaml.safe_load(_file)

    assert len(fetch_artifacts) == 1
    assert fetch_artifacts[0] == {
        "sha1": "123456",
        "target": "artifact_name",
        "url": "https://foo/bar.jar",
    }

    assert (
        "Artifact 'artifact_name' (as URL) added to fetch-artifacts-url.yaml"
        in caplog.text
    )


def test_osbs_builder_with_fetch_artifacts_url_file_creation_3(tmpdir, mocker, caplog):
    """
    Checks whether the fetch-artifacts-url.yaml file is generated with URL artifact with sha256 checksum.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.tools.urlopen")
    mocker.patch("cekit.builders.osbs.Git.push")

    tmpdir.mkdir("osbs").mkdir("repo")

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["artifacts"] = [
        {"name": "artifact_name", "sha256": "123456", "url": "https://foo/bar.jar"}
    ]

    run_osbs(descriptor, str(tmpdir), mocker)

    with open(
        os.path.join(str(tmpdir), "target", "image", "fetch-artifacts-url.yaml"), "r"
    ) as _file:
        fetch_artifacts = yaml.safe_load(_file)

    assert len(fetch_artifacts) == 1
    assert fetch_artifacts[0] == {
        "sha256": "123456",
        "target": "artifact_name",
        "url": "https://foo/bar.jar",
    }

    assert (
        "Artifact 'artifact_name' (as URL) added to fetch-artifacts-url.yaml"
        in caplog.text
    )


def test_osbs_builder_with_fetch_artifacts_url_file_creation_4(tmpdir, mocker, caplog):
    """
    Checks whether the fetch-artifacts-url.yaml file is generated with URL artifact with missing checksum.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    res = mocker.Mock()
    res.getcode.return_value = 200
    res.read.side_effect = [b"test", None]
    res.getheader.return_value = 0

    mocker.patch("cekit.tools.urlopen", return_value=res)
    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.builders.osbs.Git.push")

    tmpdir.mkdir("osbs").mkdir("repo")

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["artifacts"] = [{"url": "https://foo/bar.jar"}]

    run_osbs(descriptor, str(tmpdir), mocker)

    with open(
        os.path.join(str(tmpdir), "target", "image", "fetch-artifacts-url.yaml"), "r"
    ) as _file:
        fetch_artifacts = yaml.safe_load(_file)

    assert len(fetch_artifacts) == 1
    assert fetch_artifacts[0] == {
        "md5": "098f6bcd4621d373cade4e832627b4f6",
        "target": "bar.jar",
        "url": "https://foo/bar.jar",
    }

    assert (
        "Artifact 'bar.jar' (as URL) added to fetch-artifacts-url.yaml" in caplog.text
    )


def test_osbs_builder_with_fetch_artifacts_url_file_creation_5(tmpdir, mocker, caplog):
    """
    Checks whether the fetch-artifacts-url.yaml file is generated with URL artifact with sha256 checksum.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.tools.urlopen")
    mocker.patch("cekit.builders.osbs.Git.push")

    tmpdir.mkdir("osbs").mkdir("repo")

    res = mocker.Mock()
    res.getcode.return_value = 200
    res.read.side_effect = [b"test", None]
    res.getheader.return_value = 0

    mocker.patch("cekit.tools.urlopen", return_value=res)

    cfgcontents = """
[common]
fetch_artifact_domains = https://foo.domain, http://another.domain/path/name
ssl_verify = False
    """
    cfgfile = os.path.join(str(tmpdir), "config")
    with open(cfgfile, "w") as _file:
        _file.write(cfgcontents)

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["artifacts"] = [
        {
            "name": "artifact_name",
            "sha256": "123456",
            "url": "https://foo.domain/bar.jar",
        },
        {
            "name": "another_artifact_name",
            "sha256": "654321",
            "url": "http://another.domain/path/name/bar.jar",
        },
        {
            "name": "not_allowed_in_fetch",
            "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
            "url": "http://another.domain/wrong.jar",
        },
    ]

    run_osbs(descriptor, str(tmpdir), mocker)

    with open(
        os.path.join(str(tmpdir), "target", "image", "fetch-artifacts-url.yaml"), "r"
    ) as _file:
        fetch_artifacts = yaml.safe_load(_file)

    assert len(fetch_artifacts) == 2
    assert fetch_artifacts[0] == {
        "sha256": "123456",
        "target": "artifact_name",
        "url": "https://foo.domain/bar.jar",
    }
    assert fetch_artifacts[1] == {
        "sha256": "654321",
        "target": "another_artifact_name",
        "url": "http://another.domain/path/name/bar.jar",
    }

    assert (
        "Ignoring http://another.domain/wrong.jar as restricted to ['https://foo.domain', 'http://another.domain/path/name']"
        in caplog.text
    )
    assert "Executing 'rhpkg new-sources not_allowed_in_fetch'" in caplog.text
    assert (
        "Artifact 'artifact_name' (as URL) added to fetch-artifacts-url.yaml"
        in caplog.text
    )


def test_osbs_builder_with_fetch_artifacts_url_file_creation_multiple_hash(
    tmpdir, mocker, caplog
):
    """
    Checks whether the fetch-artifacts-url.yaml file is generated with URL artifact with multiple checksums.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    res = mocker.Mock()
    res.getcode.return_value = 200
    res.read.side_effect = [b"test", None]

    mocker.patch("cekit.tools.urlopen", return_value=res)
    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.builders.osbs.Git.push")

    tmpdir.mkdir("osbs").mkdir("repo")

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["artifacts"] = [
        {"sha256": "123456", "md5": "123456", "url": "https://foo/bar.jar"}
    ]

    run_osbs(descriptor, str(tmpdir), mocker)

    with open(
        os.path.join(str(tmpdir), "target", "image", "fetch-artifacts-url.yaml"), "r"
    ) as _file:
        fetch_artifacts = yaml.safe_load(_file)

    assert len(fetch_artifacts) == 1
    assert fetch_artifacts[0] == {
        "sha256": "123456",
        "md5": "123456",
        "target": "bar.jar",
        "url": "https://foo/bar.jar",
    }

    assert (
        "Artifact 'bar.jar' (as URL) added to fetch-artifacts-url.yaml" in caplog.text
    )


def test_osbs_builder_with_fetch_artifacts_url_file_creation_naming(
    tmpdir, mocker, caplog
):
    """
    Checks whether the fetch-artifacts-url.yaml file is generated with name specified.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    res = mocker.Mock()
    res.getcode.return_value = 200
    res.read.side_effect = [b"test", None]

    mocker.patch("cekit.tools.urlopen", return_value=res)
    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.builders.osbs.Git.push")

    tmpdir.mkdir("osbs").mkdir("repo")

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["artifacts"] = [
        {"name": "myfile.jar", "sha256": "123456", "url": "https://foo/bar.jar"}
    ]

    run_osbs(descriptor, str(tmpdir), mocker)

    with open(
        os.path.join(str(tmpdir), "target", "image", "fetch-artifacts-url.yaml"), "r"
    ) as _file:
        fetch_artifacts = yaml.safe_load(_file)

    assert len(fetch_artifacts) == 1
    assert fetch_artifacts[0] == {
        "sha256": "123456",
        "target": "myfile.jar",
        "url": "https://foo/bar.jar",
    }

    assert (
        "Artifact 'myfile.jar' (as URL) added to fetch-artifacts-url.yaml"
        in caplog.text
    )


def test_osbs_builder_with_fetch_artifacts_url_file_creation_naming_with_target(
    tmpdir, mocker, caplog
):
    """
    Checks whether the fetch-artifacts-url.yaml file is generated with name and target specified.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    res = mocker.Mock()
    res.getcode.return_value = 200
    res.read.side_effect = [b"test", None]

    mocker.patch("cekit.tools.urlopen", return_value=res)
    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.builders.osbs.Git.push")

    tmpdir.mkdir("osbs").mkdir("repo")

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["artifacts"] = [
        {
            "name": "an-additional-jar",
            "target": "myfile.jar",
            "sha256": "123456",
            "url": "https://foo/bar.jar",
        }
    ]

    run_osbs(descriptor, str(tmpdir), mocker)

    with open(
        os.path.join(str(tmpdir), "target", "image", "fetch-artifacts-url.yaml"), "r"
    ) as _file:
        fetch_artifacts = yaml.safe_load(_file)

    assert len(fetch_artifacts) == 1
    assert fetch_artifacts[0] == {
        "sha256": "123456",
        "target": "myfile.jar",
        "url": "https://foo/bar.jar",
    }

    assert (
        "Artifact 'myfile.jar' (as URL) added to fetch-artifacts-url.yaml"
        in caplog.text
    )


def test_osbs_builder_with_fetch_artifacts_url_validate_dockerfile(
    tmpdir, mocker, caplog
):
    """
    Checks whether the fetch-artifacts-url.yaml and dockerfile are generated with correct paths.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    res = mocker.Mock()
    res.getcode.return_value = 200
    res.read.side_effect = [b"test", None]

    mocker.patch("cekit.tools.urlopen", return_value=res)
    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.builders.osbs.Git.push")

    tmpdir.mkdir("osbs").mkdir("repo")

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["artifacts"] = [
        {
            "name": "an-additional-jar",
            "target": "myfile.jar",
            "sha256": "123456",
            "url": "https://foo/bar.jar",
        }
    ]

    run_osbs(descriptor, str(tmpdir), mocker)

    with open(
        os.path.join(str(tmpdir), "target", "image", "fetch-artifacts-url.yaml"), "r"
    ) as _file:
        fetch_artifacts = yaml.safe_load(_file)

    assert len(fetch_artifacts) == 1
    assert fetch_artifacts[0] == {
        "sha256": "123456",
        "target": "myfile.jar",
        "url": "https://foo/bar.jar",
    }

    with open(os.path.join(str(tmpdir), "target", "image", "Dockerfile"), "r") as _file:
        dockerfile = _file.read()

    assert "artifacts/myfile.jar" in dockerfile
    assert (
        "Artifact 'myfile.jar' (as URL) added to fetch-artifacts-url.yaml"
        in caplog.text
    )


def test_osbs_builder_with_fetch_artifacts_url_file_removal(tmpdir, mocker, caplog):
    """
    Checks whether the fetch-artifacts-url.yaml file is removed if exists
    and is not used anymore.

    https://github.com/cekit/cekit/issues/629
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.tools.urlopen")
    mocker.patch(
        "cekit.generator.osbs.get_brew_url", return_value="http://random.url/path"
    )
    mocker.patch("cekit.builders.osbs.Git.push")

    tmpdir.mkdir("osbs").mkdir("repo")

    tmpdir.join("osbs").join("repo").join("fetch-artifacts-url.yaml").write_text(
        "Some content", "utf-8"
    )

    run_osbs(image_descriptor, str(tmpdir), mocker, flag=OSBSTestFlags.RM_FETCH_FILE)

    assert not os.path.exists(
        os.path.join(str(tmpdir), "osbs", "repo", "fetch-artifacts-url.yaml")
    )
    assert "Removing old 'fetch-artifacts-url.yaml' file" in caplog.text


def test_osbs_builder_with_fetch_artifacts_url_file_source_fail(tmpdir, mocker, caplog):
    """
    Checks whether the process fails if the source-url is missing checksums.
    """
    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.tools.urlopen")
    mocker.patch("cekit.builders.osbs.Git.push")

    tmpdir.mkdir("osbs").mkdir("repo")

    res = mocker.Mock()
    res.getcode.return_value = 200
    res.read.side_effect = [b"test", None]
    res.getheader.return_value = 0

    mocker.patch("cekit.tools.urlopen", return_value=res)

    cfgcontents = """
[common]
fetch_artifact_domains = https://foo.domain, http://another.domain/path/name
ssl_verify = False
    """
    cfgfile = os.path.join(str(tmpdir), "config")
    with open(cfgfile, "w") as _file:
        _file.write(cfgcontents)

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["artifacts"] = [
        {
            "name": "artifact_name",
            "sha256": "123456",
            "url": "https://foo.domain/bar.jar",
            "source-url": "https://foo.domain/bar-source.jar",
        },
    ]

    run_osbs(descriptor, str(tmpdir), mocker, return_code=1)

    assert "Unable to add source-url for artifact" in caplog.text


def test_osbs_builder_with_fetch_artifacts_url_file_source_1(tmpdir, mocker, caplog):
    """
    Checks whether the fetch-artifacts-url.yaml file is generated with source-url.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.tools.urlopen")
    mocker.patch("cekit.builders.osbs.Git.push")

    tmpdir.mkdir("osbs").mkdir("repo")

    res = mocker.Mock()
    res.getcode.return_value = 200
    res.read.side_effect = [b"test", None]
    res.getheader.return_value = 0

    mocker.patch("cekit.tools.urlopen", return_value=res)

    cfgcontents = """
[common]
ssl_verify = False
    """
    cfgfile = os.path.join(str(tmpdir), "config")
    with open(cfgfile, "w") as _file:
        _file.write(cfgcontents)

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["artifacts"] = [
        {
            "name": "artifact_name",
            "sha256": "123456",
            "url": "https://foo.domain/bar.jar",
            "source-url": "https://foo.domain/bar-source.jar",
            "source-sha256": "123",
        },
        {
            "name": "another_artifact_name",
            "sha256": "654321",
            "url": "http://another.domain/path/name/bar.jar",
        },
    ]

    run_osbs(descriptor, str(tmpdir), mocker)

    with open(
        os.path.join(str(tmpdir), "target", "image", "fetch-artifacts-url.yaml"), "r"
    ) as _file:
        fetch_artifacts = yaml.safe_load(_file)

    assert len(fetch_artifacts) == 2
    assert fetch_artifacts[0] == {
        "sha256": "123456",
        "target": "artifact_name",
        "url": "https://foo.domain/bar.jar",
        "source-url": "https://foo.domain/bar-source.jar",
        "source-sha256": "123",
    }
    assert fetch_artifacts[1] == {
        "sha256": "654321",
        "target": "another_artifact_name",
        "url": "http://another.domain/path/name/bar.jar",
    }

    assert (
        "Artifact 'artifact_name' (as URL) added to fetch-artifacts-url.yaml"
        in caplog.text
    )
    assert (
        "Found source-url https://foo.domain/bar-source.jar and checksum markers of ['source-sha256']"
        in caplog.text
    )


def test_osbs_builder_with_fetch_artifacts_url_file_source_2(tmpdir, mocker, caplog):
    """
    Checks whether the fetch-artifacts-url.yaml file is generated with source-url and multiple checksums.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.tools.urlopen")
    mocker.patch("cekit.builders.osbs.Git.push")

    tmpdir.mkdir("osbs").mkdir("repo")

    res = mocker.Mock()
    res.getcode.return_value = 200
    res.read.side_effect = [b"test", None]
    res.getheader.return_value = 0

    mocker.patch("cekit.tools.urlopen", return_value=res)

    cfgcontents = """
[common]
ssl_verify = False
    """
    cfgfile = os.path.join(str(tmpdir), "config")
    with open(cfgfile, "w") as _file:
        _file.write(cfgcontents)

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["artifacts"] = [
        {
            "name": "artifact_name",
            "sha256": "123456",
            "url": "https://foo.domain/bar.jar",
            "source-url": "https://foo.domain/bar-source.jar",
            "source-sha256": "123",
            "source-md5": "456",
        },
        {
            "name": "another_artifact_name",
            "sha256": "654321",
            "url": "http://another.domain/path/name/bar.jar",
        },
    ]

    run_osbs(descriptor, str(tmpdir), mocker)

    with open(
        os.path.join(str(tmpdir), "target", "image", "fetch-artifacts-url.yaml"), "r"
    ) as _file:
        fetch_artifacts = yaml.safe_load(_file)

    assert len(fetch_artifacts) == 2
    assert fetch_artifacts[0] == {
        "sha256": "123456",
        "target": "artifact_name",
        "url": "https://foo.domain/bar.jar",
        "source-url": "https://foo.domain/bar-source.jar",
        "source-sha256": "123",
        "source-md5": "456",
    }
    assert fetch_artifacts[1] == {
        "sha256": "654321",
        "target": "another_artifact_name",
        "url": "http://another.domain/path/name/bar.jar",
    }

    assert (
        "Artifact 'artifact_name' (as URL) added to fetch-artifacts-url.yaml"
        in caplog.text
    )
    assert (
        "Found source-url https://foo.domain/bar-source.jar and checksum markers of ['source-sha256', 'source-md5']"
        in caplog.text
    )


def test_osbs_builder_with_fetch_artifacts_pnc_file_removal(tmpdir, mocker, caplog):
    """
    Checks whether the fetch-artifacts-pnc.yaml file is removed if exists
    and is not used anymore.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.tools.urlopen")
    mocker.patch(
        "cekit.generator.osbs.get_brew_url", return_value="http://random.url/path"
    )
    mocker.patch("cekit.builders.osbs.Git.push")

    tmpdir.mkdir("osbs").mkdir("repo")

    tmpdir.join("osbs").join("repo").join("fetch-artifacts-pnc.yaml").write_text(
        "Some content", "utf-8"
    )

    run_osbs(image_descriptor, str(tmpdir), mocker, flag=OSBSTestFlags.RM_FETCH_FILE)

    assert not os.path.exists(
        os.path.join(str(tmpdir), "osbs", "repo", "fetch-artifacts-pnc.yaml")
    )
    assert "Removing old 'fetch-artifacts-pnc.yaml' file" in caplog.text


@pytest.mark.parametrize("flag", [[], ["--redhat"]])
def test_osbs_builder_container_yaml_existence(tmpdir, mocker, caplog, flag):
    """
    Make sure that the osbs section is properly merged.
    The evidence is that the container.yaml file is generated.

    https://github.com/cekit/cekit/issues/631
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.tools.urlopen")
    mocker.patch(
        "cekit.generator.osbs.get_brew_url", return_value="http://random.url/path"
    )
    mocker.patch("cekit.builders.osbs.Git.push")

    tmpdir.mkdir("osbs").mkdir("repo")

    with Chdir(os.path.join(str(tmpdir), "osbs", "repo")):
        subprocess.run(["git", "init"])
        subprocess.run(["touch", "file"])
        subprocess.run(["git", "add", "file"])
        subprocess.run(["git", "commit", "-m", "Dummy"])

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["osbs"]["configuration"] = {
        "container": {"compose": {"pulp_repos": True}}
    }

    run_osbs(descriptor, str(tmpdir), mocker, general_command=flag)

    assert os.path.exists(os.path.join(str(tmpdir), "osbs", "repo", "container.yaml"))
    dockerfile_path = os.path.join(str(tmpdir), "target", "image", "Dockerfile")
    assert os.path.exists(dockerfile_path) is True
    with open(dockerfile_path, "r") as _file:
        dockerfile = _file.read()

    assert "COPY $REMOTE_SOURCE $REMOTE_SOURCE_DIR" not in dockerfile


def test_osbs_builder_with_cachito_enabled(tmpdir, mocker, caplog):
    """
    Checks whether the generated Dockerfile has cachito instructions if container.yaml
    file has cachito section.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.tools.urlopen")
    mocker.patch(
        "cekit.generator.osbs.get_brew_url", return_value="http://random.url/path"
    )
    mocker.patch("cekit.builders.osbs.Git.push")

    tmpdir.mkdir("osbs").mkdir("repo")

    with Chdir(os.path.join(str(tmpdir), "osbs", "repo")):
        subprocess.run(["git", "init"])
        subprocess.run(["touch", "file"])
        subprocess.run(["git", "add", "file"])
        subprocess.run(["git", "commit", "-m", "Dummy"])

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["osbs"]["configuration"] = {
        "container": {
            "remote_source": {"ref": "123456", "repo": "http://foo.bar.com"},
            "compose": {"pulp_repos": True},
        }
    }

    run_osbs(descriptor, str(tmpdir), mocker)

    dockerfile_path = os.path.join(str(tmpdir), "target", "image", "Dockerfile")
    assert os.path.exists(dockerfile_path) is True
    with open(dockerfile_path, "r") as _file:
        dockerfile = _file.read()
        assert (
            """## START target image test/image:1.0
## \\
    FROM centos:7


    USER root

    COPY $REMOTE_SOURCE $REMOTE_SOURCE_DIR
    WORKDIR $REMOTE_SOURCE_DIR/app

###### START image 'test/image:1.0'
###### \\
        # Set 'test/image' image defined environment variables
        ENV \\
            JBOSS_IMAGE_NAME="test/image" \\
            JBOSS_IMAGE_VERSION="1.0"
        # Set 'test/image' image defined labels
        LABEL \\
            foo="bar" \\
            io.cekit.version="VVVVV" \\
            labela="a" \\
            name="test/image" \\
            version="1.0"
###### /
###### END image 'test/image:1.0'

    RUN rm -rf $REMOTE_SOURCE_DIR
""".replace(
                "VVVVV", __version__
            )
            in dockerfile
        )
    assert re.search("Cachito definition is .*http://foo.bar.com", caplog.text)


@pytest.mark.skipif(
    platform.system() == "Darwin", reason="Disabled on macOS, cannot run skopeo"
)
def test_osbs_builder_with_rhpam_1(tmpdir, caplog):
    """
    Verify that multi-stage build has Cachito instructions enabled.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    shutil.copytree(
        os.path.join(os.path.dirname(__file__), "images", "rhpam1"),
        os.path.join(str(tmpdir), "rhpam"),
    )

    cfgcontents = """
[common]
redhat = True
    """
    cfgfile = os.path.join(str(tmpdir), "config.cfg")
    with open(cfgfile, "w") as _file:
        _file.write(cfgcontents)

    run_cekit(
        (os.path.join(str(tmpdir), "rhpam")),
        parameters=[
            "--config",
            cfgfile,
            "-v",
            "--work-dir",
            str(tmpdir),
            "build",
            "--dry-run",
            "osbs",
        ],
    )

    dockerfile_path = os.path.join(
        str(tmpdir), "rhpam", "target", "image", "Dockerfile"
    )
    assert os.path.exists(dockerfile_path) is True
    with open(dockerfile_path, "r") as _file:
        dockerfile = _file.read()
        print("\n" + dockerfile + "\n")
        result = """# This is a Dockerfile for the rhpam-7/rhpam-kogito-operator:7.11 image.

## START builder image operator-builder:7.11
## \\
    FROM registry.access.redhat.com/ubi8/go-toolset:1.14.12-17.1618436992 AS operator-builder
    USER root

    COPY $REMOTE_SOURCE $REMOTE_SOURCE_DIR
    WORKDIR $REMOTE_SOURCE_DIR/app

###### START module 'org.kie.kogito.builder:7.11'
###### \\
        # Copy 'org.kie.kogito.builder' module general artifacts to '/workspace/' destination
        COPY \\
            main.go \\
            /workspace/
        # Copy 'org.kie.kogito.builder' module content
        COPY modules/org.kie.kogito.builder /tmp/scripts/org.kie.kogito.builder
        # Custom scripts from 'org.kie.kogito.builder' module
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/org.kie.kogito.builder/install.sh" ]
###### /
###### END module 'org.kie.kogito.builder:7.11'

###### START image 'operator-builder:7.11'
###### \\
        # Set 'operator-builder' image defined environment variables
        ENV \\
            JBOSS_IMAGE_NAME="rhpam-7/rhpam-kogito-operator" \\
            JBOSS_IMAGE_VERSION="7.11"
        # Set 'operator-builder' image defined labels
        LABEL \\
            name="rhpam-7/rhpam-kogito-operator" \\
            version="7.11"
###### /
###### END image 'operator-builder:7.11'

    RUN rm -rf $REMOTE_SOURCE_DIR

## /
## END builder image

## START target image rhpam-7/rhpam-kogito-operator:7.11
## \\
    FROM registry.access.redhat.com/ubi8/ubi-minimal:latest


    USER root

###### START image 'rhpam-7/rhpam-kogito-operator:7.11'
###### \\
        # Copy 'rhpam-7/rhpam-kogito-operator' image stage artifacts
        COPY --from=operator-builder /workspace/rhpam-kogito-operator-manager /usr/local/bin/rhpam-kogito-operator-manager
        # Set 'rhpam-7/rhpam-kogito-operator' image defined environment variables
        ENV \\
            JBOSS_IMAGE_NAME="rhpam-7/rhpam-kogito-operator" \\
            JBOSS_IMAGE_VERSION="7.11"
        # Set 'rhpam-7/rhpam-kogito-operator' image defined labels
        LABEL \\
            com.redhat.component="rhpam-7-kogito-rhel8-operator-container" \\
            description="Runtime Image for the RHPAM Kogito Operator" \\
            io.cekit.version="VVVVV" \\
            io.k8s.description="Operator for deploying RHPAM Kogito Application" \\
            io.k8s.display-name="Red Hat PAM Kogito Operator" \\
            io.openshift.tags="rhpam,kogito,operator" \\
            maintainer="bsig-cloud@redhat.com" \\
            name="rhpam-7/rhpam-kogito-operator" \\
            summary="Runtime Image for the RHPAM Kogito Operator" \\
            version="7.11"
###### /
###### END image 'rhpam-7/rhpam-kogito-operator:7.11'



    # Switch to 'root' user and remove artifacts and modules
    USER root
    RUN rm -rf "/tmp/scripts" "/tmp/artifacts"
    # Define the user
    USER 1001
## /
## END target image""".replace(
            "VVVVV", __version__
        )
        #            )
        # Verify the nested ubi-minimal has been updated but then revert it back to
        # a static value for easier comparisons.
        assert re.search(r"ubi-minimal:\d\.\d+-(\d|\.)+", dockerfile)
        dockerfile = re.sub(
            r"ubi-minimal:\d\.\d+-(\d|\.)+", "ubi-minimal:latest", dockerfile
        )
        assert result in dockerfile
    container_path = os.path.join(
        str(tmpdir), "rhpam", "target", "image", "container.yaml"
    )
    assert os.path.exists(container_path) is True
    with open(container_path, "r") as _file:
        containerfile = _file.read()
        print("\n" + containerfile + "\n")
        assert (
            """image_build_method: imagebuilder
platforms:
  only:
  - x86_64
remote_source:
  pkg_managers:
  - gomod
  ref: db4a5d18f5f52a64083d8f1bd1776ad60a46904c
  repo: https://github.com/kiegroup/rhpam-kogito-operator"""
            in containerfile
        )


def test_osbs_builder_with_rhpam_2(tmpdir, caplog):
    """
    Verify that multi-stage build with dual configuration/container (for Cachito) will fail.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    shutil.copytree(
        os.path.join(os.path.dirname(__file__), "images", "rhpam2"),
        os.path.join(str(tmpdir), "rhpam"),
    )

    cfgcontents = """
    """
    cfgfile = os.path.join(str(tmpdir), "config.cfg")
    with open(cfgfile, "w") as _file:
        _file.write(cfgcontents)

    with Chdir(os.path.join(str(tmpdir), "rhpam")):
        result = CliRunner().invoke(
            cli,
            [
                "--config",
                cfgfile,
                "-v",
                "--work-dir",
                str(tmpdir),
                "build",
                "--dry-run",
                "osbs",
            ],
            catch_exceptions=True,
        )
        sys.stdout.write("\n")
        sys.stdout.write(result.output)

        assert result.exit_code == 1

    assert "Found multiple container definitions " in caplog.text


def test_osbs_builder_with_rhpam_3(tmpdir, caplog):
    """
    Verify that multi-stage build has Cachito instructions enabled.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    shutil.copytree(
        os.path.join(os.path.dirname(__file__), "images", "rhpam3"),
        os.path.join(str(tmpdir), "rhpam"),
    )

    cfgcontents = """
[common]
redhat = True
    """
    cfgfile = os.path.join(str(tmpdir), "config.cfg")
    with open(cfgfile, "w") as _file:
        _file.write(cfgcontents)

    run_cekit(
        (os.path.join(str(tmpdir), "rhpam")),
        parameters=[
            "--config",
            cfgfile,
            "-v",
            "--work-dir",
            str(tmpdir),
            "build",
            "--dry-run",
            "osbs",
        ],
    )

    dockerfile_path = os.path.join(
        str(tmpdir), "rhpam", "target", "image", "Dockerfile"
    )
    assert os.path.exists(dockerfile_path) is True
    with open(dockerfile_path, "r") as _file:
        dockerfile = _file.read()
        print("\n" + dockerfile + "\n")
        assert (
            """# This is a Dockerfile for the rhpam-7/rhpam-kogito-operator:7.11 image.

## START builder image operator-builder-one:7.11
## \\
    FROM registry.access.redhat.com/ubi8/go-toolset:1.14.12 AS operator-builder-one
    USER root

###### START module 'org.kie.kogito.builder:7.11'
###### \\
        # Copy 'org.kie.kogito.builder' module general artifacts to '/workspace/' destination
        COPY \\
            main.go \\
            /workspace/
        # Copy 'org.kie.kogito.builder' module content
        COPY modules/org.kie.kogito.builder /tmp/scripts/org.kie.kogito.builder
        # Custom scripts from 'org.kie.kogito.builder' module
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/org.kie.kogito.builder/install.sh" ]
###### /
###### END module 'org.kie.kogito.builder:7.11'

###### START image 'operator-builder-one:7.11'
###### \\
        # Set 'operator-builder-one' image defined environment variables
        ENV \\
            JBOSS_IMAGE_NAME="rhpam-7/rhpam-kogito-operator" \\
            JBOSS_IMAGE_VERSION="7.11"
        # Set 'operator-builder-one' image defined labels
        LABEL \\
            name="rhpam-7/rhpam-kogito-operator" \\
            version="7.11"
###### /
###### END image 'operator-builder-one:7.11'


## /
## END builder image
## START builder image operator-builder-two:7.11
## \\
    FROM registry.access.redhat.com/ubi8/go-toolset:1.14.12 AS operator-builder-two
    USER root

    COPY $REMOTE_SOURCE $REMOTE_SOURCE_DIR
    WORKDIR $REMOTE_SOURCE_DIR/app

###### START image 'operator-builder-two:7.11'
###### \\
        # Set 'operator-builder-two' image defined environment variables
        ENV \\
            JBOSS_IMAGE_NAME="rhpam-7/rhpam-kogito-operator" \\
            JBOSS_IMAGE_VERSION="7.11"
        # Set 'operator-builder-two' image defined labels
        LABEL \\
            name="rhpam-7/rhpam-kogito-operator" \\
            version="7.11"
###### /
###### END image 'operator-builder-two:7.11'

    RUN rm -rf $REMOTE_SOURCE_DIR

## /
## END builder image

## START target image rhpam-7/rhpam-kogito-operator:7.11
## \\
    FROM registry.access.redhat.com/ubi8/ubi-minimal:latest


    USER root

###### START image 'rhpam-7/rhpam-kogito-operator:7.11'
###### \\
        # Copy 'rhpam-7/rhpam-kogito-operator' image stage artifacts
        COPY --from=operator-builder /workspace/rhpam-kogito-operator-manager /usr/local/bin/rhpam-kogito-operator-manager
        # Set 'rhpam-7/rhpam-kogito-operator' image defined environment variables
        ENV \\
            JBOSS_IMAGE_NAME="rhpam-7/rhpam-kogito-operator" \\
            JBOSS_IMAGE_VERSION="7.11"
        # Set 'rhpam-7/rhpam-kogito-operator' image defined labels
        LABEL \\
            com.redhat.component="rhpam-7-kogito-rhel8-operator-container" \\
            description="Runtime Image for the RHPAM Kogito Operator" \\
            io.cekit.version="VVVVV" \\
            io.k8s.description="Operator for deploying RHPAM Kogito Application" \\
            io.k8s.display-name="Red Hat PAM Kogito Operator" \\
            io.openshift.tags="rhpam,kogito,operator" \\
            maintainer="bsig-cloud@redhat.com" \\
            name="rhpam-7/rhpam-kogito-operator" \\
            summary="Runtime Image for the RHPAM Kogito Operator" \\
            version="7.11"
###### /
###### END image 'rhpam-7/rhpam-kogito-operator:7.11'



    # Switch to 'root' user and remove artifacts and modules
    USER root
    RUN rm -rf "/tmp/scripts" "/tmp/artifacts"
    # Define the user
    USER 1001
## /
## END target image""".replace(
                "VVVVV", __version__
            )
            in dockerfile
        )
    container_path = os.path.join(
        str(tmpdir), "rhpam", "target", "image", "container.yaml"
    )
    assert os.path.exists(container_path) is True
    with open(container_path, "r") as _file:
        containerfile = _file.read()
        print("\n" + containerfile + "\n")
        assert (
            """image_build_method: imagebuilder
platforms:
  only:
  - x86_64
remote_source:
  pkg_managers:
  - gomod
  ref: db4a5d18f5f52a64083d8f1bd1776ad60a46904c
  repo: https://github.com/kiegroup/rhpam-kogito-operator"""
            in containerfile
        )


def test_osbs_builder_with_fetch_artifacts_pnc_file_creation_1(tmpdir, mocker, caplog):
    """
    Checks whether the fetch-artifacts-pnc.yaml file is generated with correct artifact ids.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.tools.urlopen")
    mocker.patch("cekit.builders.osbs.Git.push")

    tmpdir.mkdir("osbs").mkdir("repo")

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["artifacts"] = [
        {"pnc_build_id": "123456", "pnc_artifact_id": "54321", "name": "foo.jar"}
    ]

    run_osbs(descriptor, str(tmpdir), mocker)

    with open(
        os.path.join(str(tmpdir), "target", "image", "fetch-artifacts-pnc.yaml"), "r"
    ) as _file:
        fetch_artifacts = yaml.safe_load(_file)

    assert "Executing '['rhpkg', 'new-sources', 'foo.jar']'" not in caplog.text
    assert fetch_artifacts["builds"] == [
        {"build_id": "123456", "artifacts": [{"id": "54321", "target": "foo.jar"}]}
    ]


def test_osbs_builder_with_fetch_artifacts_pnc_file_creation_2(tmpdir, mocker, caplog):
    """
    Checks whether the fetch-artifacts-pnc.yaml file is generated with correct artifact ids.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.tools.urlopen")
    mocker.patch("cekit.builders.osbs.Git.push")

    tmpdir.mkdir("osbs").mkdir("repo")

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["artifacts"] = [
        {"target": "boo.jar", "pnc_build_id": "123456", "pnc_artifact_id": "00001"},
        {
            "target": "foo.jar",
            "pnc_build_id": "123456",
            "pnc_artifact_id": "54321",
            "url": "http://www.dummy.com/build/artifact.jar",
        },
        {
            "target": "foobar/goo.zip",
            "pnc_build_id": "987654",
            "pnc_artifact_id": "00002",
        },
    ]

    run_osbs(descriptor, str(tmpdir), mocker)

    with open(
        os.path.join(str(tmpdir), "target", "image", "fetch-artifacts-pnc.yaml"), "r"
    ) as _file:
        fetch_artifacts = _file.read()
    with open(
        os.path.join(str(tmpdir), "target", "image", "fetch-artifacts-pnc.yaml"), "r"
    ) as _file:
        fetch_artifacts_yaml = yaml.safe_load(_file)
    print(f"Read fetch_pnc_artifacts {fetch_artifacts}\n")
    assert "# Created by CEKit version" in fetch_artifacts
    assert fetch_artifacts_yaml["builds"] == [
        {
            "build_id": "123456",
            "artifacts": [
                {"id": "00001", "target": "boo.jar"},
                {"id": "54321", "target": "foo.jar"},
            ],
        },
        {
            "build_id": "987654",
            "artifacts": [{"id": "00002", "target": "foobar/goo.zip"}],
        },
    ]
    assert (
        """builds:
- build_id: '123456'
  artifacts:
  - id: '00001'
    target: boo.jar
  - id: '54321' # http://www.dummy.com/build/artifact.jar
    target: foo.jar
- build_id: '987654'
  artifacts:
  - id: '00002'
    target: foobar/goo.zip"""
        in fetch_artifacts
    )
    with open(os.path.join(str(tmpdir), "target", "image", "Dockerfile"), "r") as _file:
        dockerfile = _file.read()
    assert (
        """COPY \\
            artifacts/boo.jar \\
            artifacts/foo.jar \\
            artifacts/foobar/goo.zip \\
            /tmp/artifacts/"""
        in dockerfile
    )


def test_osbs_builder_with_brew_and_lookaside(tmpdir, mocker, caplog):
    """
    Checks whether the fetch-artifacts-url.yaml file is generated with plain artifact.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")
    mocker.patch("cekit.crypto.get_sum", return_value="123456")
    mocker.patch("cekit.cache.artifact.get_sum", return_value="123456")
    mocker.patch("cekit.tools.decision", return_value=True)
    mocker.patch("cekit.tools.urlopen")
    mocker.patch(
        "cekit.generator.osbs.get_brew_url", return_value="http://random.url/path"
    )
    mocker.patch("cekit.builders.osbs.Git.push")

    work_dir = str(tmpdir.mkdir("work_dir"))
    image_dir = str(tmpdir)
    os.makedirs(work_dir + "/cache")
    with open(os.path.join(image_dir, "config"), "w") as fd:
        fd.write("[common]\n")
        fd.write("cache_url = #filename#\n")
    with open(os.path.join(image_dir, "artifact_name"), "w") as fd:
        fd.write("jar-content")

    tmpdir.mkdir("osbs").mkdir("repo")

    tmpdir.join("osbs").join("repo").join("fetch-artifacts-url.yaml").write_text(
        "Some content", "utf-8"
    )

    descriptor = copy.deepcopy(image_descriptor)

    descriptor["artifacts"] = [{"name": "artifact_name", "sha256": "123456"}]

    run_osbs(descriptor, str(tmpdir), mocker)

    assert (
        "Unable to use Brew as artifact does not have md5 checksum defined"
        in caplog.text
    )
    assert (
        "Plain artifact artifact_name could not be found in Brew, trying to handle it using lookaside cache"
        in caplog.text
    )


def test_osbs_builder_with_follow_tag_non_rh(tmpdir):
    """
    Verify that follow_tag requires rh flag.
    """

    shutil.copytree(
        os.path.join(os.path.dirname(__file__), "images", "rhpam1"),
        os.path.join(str(tmpdir), "rhpam"),
    )

    cfgcontents = """
    """
    cfgfile = os.path.join(str(tmpdir), "config.cfg")
    with open(cfgfile, "w") as _file:
        _file.write(cfgcontents)

    run_cekit(
        (os.path.join(str(tmpdir), "rhpam")),
        parameters=[
            "--config",
            cfgfile,
            "-v",
            "--work-dir",
            str(tmpdir),
            "build",
            "--dry-run",
            "osbs",
        ],
        message="follow_tag annotation only supported with redhat flag",
        return_code=1,
    )


def test_osbs_builder_kick_build_with_tag_1(tmpdir, mocker, caplog):
    """
    Does push sources to dist-git and tags afterwards.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    source_dir = tmpdir.mkdir("source")
    repo_dir = source_dir.mkdir("osbs").mkdir("repo")

    mocker.patch("cekit.tools.decision", return_value=True)

    descriptor = copy.deepcopy(image_descriptor)

    mock_run = run_osbs(
        descriptor,
        str(source_dir),
        mocker,
        build_command=["build", "osbs", "--release", "--tag", "FOOBAR"],
    )

    assert os.path.exists(str(repo_dir.join("Dockerfile"))) is True

    mock_run.assert_has_calls(
        [
            mocker.call(
                ["git", "add", "--all", "Dockerfile"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
            mocker.call(
                ["git", "push", "-q", "origin", "branch"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
            mocker.call(
                [
                    "git",
                    "commit",
                    "-q",
                    "-m",
                    "Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb",
                ],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
        ],
        any_order=True,
    )

    assert (
        "Committing with message: 'Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb'"
        in caplog.text
    )
    assert "Image was built successfully in OSBS!" in caplog.text
    assert (
        "Tagging git repository (git+https://somehost.com/git/containers/somerepo#3b9283cb26b35511517ff5c0c3e11f490cba8feb) with FOOBAR-1 from build 123456"
        in caplog.text
    )
    assert (
        "Tagging git repository (https://my.cekit.repo/foo) with FOOBAR-1 from build 123456"
        in caplog.text
    )


def test_osbs_builder_kick_build_with_tag_2(tmpdir, mocker, caplog):
    """
    Does push sources to dist-git and tags afterwards.
    """

    caplog.set_level(logging.DEBUG, logger="cekit")

    source_dir = tmpdir.mkdir("source")
    repo_dir = source_dir.mkdir("osbs").mkdir("repo")

    mocker.patch("cekit.tools.decision", return_value=True)

    descriptor = copy.deepcopy(image_descriptor)

    mock_run = run_osbs(
        descriptor,
        str(source_dir),
        mocker,
        build_command=["build", "osbs", "--release", "--tag"],
    )

    assert os.path.exists(str(repo_dir.join("Dockerfile"))) is True

    mock_run.assert_has_calls(
        [
            mocker.call(
                ["git", "add", "--all", "Dockerfile"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
            mocker.call(
                ["git", "push", "-q", "origin", "branch"],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
            mocker.call(
                [
                    "git",
                    "commit",
                    "-q",
                    "-m",
                    "Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb",
                ],
                stderr=None,
                stdout=None,
                check=True,
                universal_newlines=True,
            ),
        ],
        any_order=True,
    )

    assert (
        "Committing with message: 'Sync with path, commit 3b9283cb26b35511517ff5c0c3e11f490cba8feb'"
        in caplog.text
    )
    assert "Image was built successfully in OSBS!" in caplog.text
    assert (
        "Tagging git repository (git+https://somehost.com/git/containers/somerepo#3b9283cb26b35511517ff5c0c3e11f490cba8feb) with test-image-1.0-1 from build 123456"
        in caplog.text
    )
    assert (
        "Tagging git repository (https://my.cekit.repo/foo) with test-image-1.0-1 from build 123456"
        in caplog.text
    )


def test_osbs_builder_kick_build_with_tag_3(tmpdir):
    """
    Verify tag and release flags.
    """
    run_cekit(
        str(tmpdir),
        parameters=[
            "-v",
            "build",
            "osbs",
            "--tag",
        ],
        message="--tag requires --release as scratch builds cannot be tagged",
        return_code=2,
    )
