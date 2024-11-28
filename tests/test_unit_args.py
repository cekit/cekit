import importlib
import sys

import pytest
from click.testing import CliRunner

from cekit.cli import cli


def _get_class_by_name(clazz):
    module_name, class_name = clazz.rsplit(".", 1)

    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)

    return cls


@pytest.mark.parametrize(
    "args,clazz,params",
    [
        # Check custom target
        (
            ["--redhat", "build", "docker"],
            "cekit.builders.docker_builder.DockerBuilder",
            {
                "build_args": (),
                "build_flag": (),
                "container_file": None,
                "descriptor": "image.yaml",
                "verbose": False,
                "nocolor": False,
                "work_dir": "~/.cekit",
                "config": "~/.cekit/config",
                "redhat": True,
                "target": "target",
                "trace": False,
                "validate": False,
                "dry_run": False,
                "overrides": (),
                "pull": False,
                "no_squash": False,
                "tags": (),
                "platform": None,
            },
        ),
        # Check custom target
        (
            ["--target", "custom-target", "build", "docker"],
            "cekit.builders.docker_builder.DockerBuilder",
            {
                "build_args": (),
                "build_flag": (),
                "container_file": None,
                "descriptor": "image.yaml",
                "verbose": False,
                "nocolor": False,
                "work_dir": "~/.cekit",
                "config": "~/.cekit/config",
                "redhat": False,
                "target": "custom-target",
                "trace": False,
                "validate": False,
                "dry_run": False,
                "overrides": (),
                "pull": False,
                "no_squash": False,
                "tags": (),
                "platform": None,
            },
        ),
        # Check custom work dir
        (
            ["--work-dir", "custom-workdir", "build", "docker"],
            "cekit.builders.docker_builder.DockerBuilder",
            {
                "build_args": (),
                "build_flag": (),
                "container_file": None,
                "descriptor": "image.yaml",
                "verbose": False,
                "nocolor": False,
                "work_dir": "custom-workdir",
                "config": "~/.cekit/config",
                "redhat": False,
                "target": "target",
                "trace": False,
                "validate": False,
                "dry_run": False,
                "overrides": (),
                "pull": False,
                "no_squash": False,
                "tags": (),
                "platform": None,
            },
        ),
        # Check custom config file
        (
            ["--config", "custom-config", "build", "docker"],
            "cekit.builders.docker_builder.DockerBuilder",
            {
                "build_args": (),
                "build_flag": (),
                "container_file": None,
                "descriptor": "image.yaml",
                "verbose": False,
                "nocolor": False,
                "work_dir": "~/.cekit",
                "config": "custom-config",
                "redhat": False,
                "target": "target",
                "trace": False,
                "validate": False,
                "dry_run": False,
                "overrides": (),
                "pull": False,
                "no_squash": False,
                "tags": (),
                "platform": None,
            },
        ),
        # Test default values for Docker builder
        (
            ["build", "docker"],
            "cekit.builders.docker_builder.DockerBuilder",
            {
                "build_args": (),
                "build_flag": (),
                "container_file": None,
                "descriptor": "image.yaml",
                "verbose": False,
                "nocolor": False,
                "work_dir": "~/.cekit",
                "config": "~/.cekit/config",
                "redhat": False,
                "target": "target",
                "trace": False,
                "validate": False,
                "dry_run": False,
                "overrides": (),
                "pull": False,
                "no_squash": False,
                "tags": (),
                "platform": None,
            },
        ),
        # Test overrides
        (
            ["build", "--overrides", "foo", "--overrides-file", "bar", "docker"],
            "cekit.builders.docker_builder.DockerBuilder",
            {
                "build_args": (),
                "build_flag": (),
                "container_file": None,
                "descriptor": "image.yaml",
                "verbose": False,
                "nocolor": False,
                "work_dir": "~/.cekit",
                "config": "~/.cekit/config",
                "redhat": False,
                "target": "target",
                "trace": False,
                "validate": False,
                "dry_run": False,
                "overrides": ("foo", "bar"),
                "pull": False,
                "no_squash": False,
                "tags": (),
                "platform": None,
            },
        ),
        # Test default values for OSBS builder
        (
            ["build", "osbs"],
            "cekit.builders.osbs.OSBSBuilder",
            {
                "container_file": None,
                "descriptor": "image.yaml",
                "verbose": False,
                "nocolor": False,
                "work_dir": "~/.cekit",
                "config": "~/.cekit/config",
                "redhat": False,
                "target": "target",
                "trace": False,
                "validate": False,
                "dry_run": False,
                "overrides": (),
                "nowait": False,
                "release": False,
                "user": None,
                "stage": False,
                "sync_only": False,
                "tag": None,
                "commit_message": None,
                "assume_yes": False,
            },
        ),
        # Test setting user for OSBS
        (
            ["build", "osbs", "--user", "SOMEUSER"],
            "cekit.builders.osbs.OSBSBuilder",
            {
                "container_file": None,
                "descriptor": "image.yaml",
                "verbose": False,
                "nocolor": False,
                "work_dir": "~/.cekit",
                "config": "~/.cekit/config",
                "redhat": False,
                "target": "target",
                "trace": False,
                "validate": False,
                "dry_run": False,
                "overrides": (),
                "nowait": False,
                "release": False,
                "user": "SOMEUSER",
                "stage": False,
                "sync_only": False,
                "tag": None,
                "commit_message": None,
                "assume_yes": False,
            },
        ),
        # Test setting stage environment for OSBS
        (
            ["build", "osbs", "--stage"],
            "cekit.builders.osbs.OSBSBuilder",
            {
                "container_file": None,
                "descriptor": "image.yaml",
                "verbose": False,
                "nocolor": False,
                "work_dir": "~/.cekit",
                "config": "~/.cekit/config",
                "redhat": False,
                "target": "target",
                "trace": False,
                "validate": False,
                "dry_run": False,
                "overrides": (),
                "nowait": False,
                "release": False,
                "user": None,
                "stage": True,
                "sync_only": False,
                "tag": None,
                "commit_message": None,
                "assume_yes": False,
            },
        ),
        # Test setting nowait for OSBS
        (
            ["build", "osbs", "--nowait"],
            "cekit.builders.osbs.OSBSBuilder",
            {
                "container_file": None,
                "descriptor": "image.yaml",
                "verbose": False,
                "nocolor": False,
                "work_dir": "~/.cekit",
                "config": "~/.cekit/config",
                "redhat": False,
                "target": "target",
                "trace": False,
                "validate": False,
                "dry_run": False,
                "overrides": (),
                "nowait": True,
                "release": False,
                "user": None,
                "stage": False,
                "sync_only": False,
                "tag": None,
                "commit_message": None,
                "assume_yes": False,
            },
        ),
        (
            ["test", "--image", "image:1.0", "behave"],
            "cekit.test.behave_tester.BehaveTester",
            {
                "descriptor": "image.yaml",
                "verbose": False,
                "nocolor": False,
                "work_dir": "~/.cekit",
                "config": "~/.cekit/config",
                "redhat": False,
                "target": "target",
                "trace": False,
                "overrides": (),
                "image": "image:1.0",
                "steps_url": "https://github.com/cekit/behave-test-steps.git",
                "steps_ref": "v1",
                "wip": False,
                "include_re": None,
                "exclude_re": None,
                "names": (),
            },
        ),
        (
            ["build", "docker", "--pull"],
            "cekit.builders.docker_builder.DockerBuilder",
            {
                "build_args": (),
                "build_flag": (),
                "container_file": None,
                "descriptor": "image.yaml",
                "verbose": False,
                "nocolor": False,
                "work_dir": "~/.cekit",
                "config": "~/.cekit/config",
                "redhat": False,
                "target": "target",
                "trace": False,
                "validate": False,
                "dry_run": False,
                "overrides": (),
                "pull": True,
                "no_squash": False,
                "tags": (),
                "platform": None,
            },
        ),
        (
            ["build", "osbs"],
            "cekit.builders.osbs.OSBSBuilder",
            {
                "container_file": None,
                "descriptor": "image.yaml",
                "verbose": False,
                "nocolor": False,
                "work_dir": "~/.cekit",
                "config": "~/.cekit/config",
                "redhat": False,
                "target": "target",
                "trace": False,
                "validate": False,
                "dry_run": False,
                "overrides": (),
                "release": False,
                "user": None,
                "nowait": False,
                "stage": False,
                "sync_only": False,
                "tag": None,
                "commit_message": None,
                "assume_yes": False,
            },
        ),
        (
            ["build", "docker"],
            "cekit.builders.docker_builder.DockerBuilder",
            {
                "build_args": (),
                "build_flag": (),
                "container_file": None,
                "descriptor": "image.yaml",
                "verbose": False,
                "nocolor": False,
                "work_dir": "~/.cekit",
                "config": "~/.cekit/config",
                "redhat": False,
                "target": "target",
                "trace": False,
                "validate": False,
                "dry_run": False,
                "overrides": (),
                "pull": False,
                "no_squash": False,
                "tags": (),
                "platform": None,
            },
        ),
        (
            ["build", "buildah"],
            "cekit.builders.buildah.BuildahBuilder",
            {
                "container_file": None,
                "descriptor": "image.yaml",
                "verbose": False,
                "nocolor": False,
                "work_dir": "~/.cekit",
                "config": "~/.cekit/config",
                "redhat": False,
                "target": "target",
                "trace": False,
                "validate": False,
                "dry_run": False,
                "overrides": (),
                "pull": False,
                "tags": (),
                "build_args": (),
                "build_flag": (),
                "platform": None,
                "no_squash": False,
            },
        ),
    ],
)
def test_args_command(mocker, args, clazz, params):
    cekit_class = mocker.patch("cekit.cli.Cekit")
    cekit_object = mocker.Mock()
    cekit_class.return_value = cekit_object
    result = CliRunner().invoke(cli, args, catch_exceptions=False)
    sys.stdout.write("\n")
    sys.stdout.write(result.output)

    cls = _get_class_by_name(clazz)

    cekit_class.assert_called_once_with(params)
    cekit_object.run.assert_called_once_with(cls)


def test_args_not_valid_command():
    result = CliRunner().invoke(cli, ["explode"], catch_exceptions=False)
    sys.stdout.write("\n")
    sys.stdout.write(result.output)

    assert isinstance(result.exception, SystemExit)
    assert "No such command 'explode'" in result.output
    assert result.exit_code == 2


def test_args_invalid_build_engine():
    result = CliRunner().invoke(cli, ["build", "rocketscience"], catch_exceptions=False)
    sys.stdout.write("\n")
    sys.stdout.write(result.output)

    assert isinstance(result.exception, SystemExit)
    assert "No such command 'rocketscience'" in result.output
    assert result.exit_code == 2
