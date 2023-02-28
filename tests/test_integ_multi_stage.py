# -*- encoding: utf-8 -*-

from __future__ import print_function

import os
import shutil

import yaml
from click.testing import CliRunner

from cekit.cli import cli
from cekit.tools import Chdir

image_descriptor = {
    "schema_version": 1,
    "from": "centos:7",
    "name": "test/image",
    "version": "1.0",
    "labels": [{"name": "foo", "value": "bar"}, {"name": "labela", "value": "a"}],
    "envs": [{"name": "baz", "value": "qux"}, {"name": "enva", "value": "a"}],
    "run": {"cmd": ["sleep", "60"]},
}

template_teststr = "This string does not occur in the default help.md template."


def check_file_text(image_dir, match, filename="Containerfile"):
    with open(os.path.join(image_dir, "target", "image", filename), "r") as fd:
        file_content = fd.read()
        if match in file_content:
            return True
    return False


def run_cekit(image_dir, args=None, env=None):
    if args is None:
        args = ["build", "--dry-run", "docker"]

    if env is None:
        env = {}

    with Chdir(image_dir):
        result = CliRunner(env=env).invoke(cli, args, catch_exceptions=False)
        assert result.exit_code == 0
        return result


def test_multi_stage_single_image_in_list(tmpdir):
    """
    Build simple image which is a regular image, but the
    difference is that it is defined in an array in image
    descriptor
    """
    tmpdir = str(tmpdir)

    with open(os.path.join(tmpdir, "image.yaml"), "w") as fd:
        yaml.dump([image_descriptor], fd, default_flow_style=False)

    run_cekit(tmpdir, ["-v", "build", "podman"], env={"BUILDAH_LAYERS": "false"})

    assert (
        os.path.exists(os.path.join(tmpdir, "target", "image", "Containerfile")) is True
    )
    assert check_file_text(tmpdir, "ADD help.md /") is False


def test_multi_stage_proper_image(tmpdir):
    """
    Build multi-stage image.
    """
    tmpdir = str(tmpdir)

    shutil.copytree(
        os.path.join(os.path.dirname(__file__), "images", "multi-stage"),
        os.path.join(tmpdir, "multi-stage"),
    )

    # The 'BUILDAH_LAYERS' environment variable is required to not cache intermediate layers
    # See: https://bugzilla.redhat.com/show_bug.cgi?id=1746022
    run_cekit(
        os.path.join(tmpdir, "multi-stage"),
        args=["-v", "build", "podman"],
        env={"BUILDAH_LAYERS": "false"},
    )


def test_multi_stage_with_scratch_target_image(tmpdir):
    """
    Build multi-stage image. Resulting image uses a "scratch" base image and
    artifact from the builder image.
    """
    tmpdir = str(tmpdir)

    shutil.copytree(
        os.path.join(os.path.dirname(__file__), "images", "multi-stage-scratch"),
        os.path.join(tmpdir, "multi-stage-scratch"),
    )

    # The 'BUILDAH_LAYERS' environment variable is required to not cache intermediate layers
    # See: https://bugzilla.redhat.com/show_bug.cgi?id=1746022
    run_cekit(
        os.path.join(tmpdir, "multi-stage-scratch"),
        args=["-v", "build", "podman"],
        env={"BUILDAH_LAYERS": "false"},
    )
