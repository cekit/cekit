# -*- encoding: utf-8 -*-

import os
import platform
import shutil
import sys
import tempfile

import pytest
import yaml
from click.testing import CliRunner

from cekit.cli import cli
from cekit.tools import Chdir

image_descriptors = [
    {
        "schema_version": 1,
        "from": "alpine:3.9",
        "name": "test/image",
        "version": "1.0",
        "labels": [{"name": "foo", "value": "bar"}, {"name": "labela", "value": "a"}],
        "envs": [{"name": "baz", "value": "qux"}, {"name": "enva", "value": "a"}],
        "run": {"cmd": ["tail", "-f", "/dev/null"]},
    },
    {
        "schema_version": 1,
        "from": "alpine:3.9",
        "name": "image",
        "version": "1.0-slim",
        "labels": [{"name": "foo", "value": "bar"}, {"name": "labela", "value": "a"}],
        "envs": [{"name": "baz", "value": "qux"}, {"name": "enva", "value": "a"}],
        "run": {"cmd": ["tail", "-f", "/dev/null"]},
    }
]


@pytest.fixture(scope="function", name="build_image", params=image_descriptors)
def fixture_build_image(request):
    def _build_image(overrides=None):
        image_descriptor = request.param
        image_dir = tempfile.mkdtemp(prefix="tmp-cekit-test")

        with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
            yaml.dump(image_descriptor, fd, default_flow_style=False)

        args = ["-v", "build"]

        if overrides:
            args += ["--overrides", overrides]

        args.append("docker")

        with Chdir(image_dir):
            result = CliRunner().invoke(cli, args, catch_exceptions=False)

        sys.stdout.write("\n")
        sys.stdout.write(result.output)

        assert result.exit_code == 0

        return image_dir

    return _build_image


@pytest.mark.skipif(
    os.path.exists("/var/run/docker.sock") is False, reason="No Docker available"
)
def test_execute_simple_behave_test(build_image):
    feature = """@test
Feature: Basic tests

  Scenario: Check that the labels are correctly set
    Given image is built
    Then the image should contain label foo with value bar
     And the image should contain label labela with value a
    """

    test_image_dir = build_image()

    features_dir = os.path.join(test_image_dir, "tests", "features")

    os.makedirs(features_dir)

    with open(os.path.join(features_dir, "basic.feature"), "w") as fd:
        fd.write(feature)

    with Chdir(test_image_dir):
        result = CliRunner().invoke(
            cli, ["-v", "test", "behave"], catch_exceptions=False
        )

    sys.stdout.write("\n")
    sys.stdout.write(result.output)

    assert result.exit_code == 0
    assert "1 feature passed, 0 failed, 0 skipped" in result.output
    assert "1 scenario passed, 0 failed, 0 skipped" in result.output
    assert "3 steps passed, 0 failed, 0 skipped, 0 undefined" in result.output

    shutil.rmtree(os.path.join(test_image_dir, "target"), ignore_errors=True)


@pytest.mark.skipif(
    os.path.exists("/var/run/docker.sock") is False, reason="No Docker available"
)
def test_execute_simple_behave_test_with_overrides(build_image):
    feature = """@different
Feature: Basic tests

  Scenario: Check that the labels are correctly set
    Given image is built
    Then the image should contain label foo with value bar
     And the image should contain label labela with value a
    """

    overrides = '{"name": "different/image"}'

    test_image_dir = build_image(overrides)

    features_dir = os.path.join(test_image_dir, "tests", "features")

    os.makedirs(features_dir)

    with open(os.path.join(features_dir, "basic.feature"), "w") as fd:
        fd.write(feature)

    with Chdir(test_image_dir):
        result = CliRunner().invoke(
            cli,
            ["-v", "test", "--overrides", overrides, "behave"],
            catch_exceptions=False,
        )

    sys.stdout.write("\n")
    sys.stdout.write(result.output)

    assert result.exit_code == 0
    assert "1 feature passed, 0 failed, 0 skipped" in result.output
    assert "1 scenario passed, 0 failed, 0 skipped" in result.output
    assert "3 steps passed, 0 failed, 0 skipped, 0 undefined" in result.output

    shutil.rmtree(os.path.join(test_image_dir, "target"), ignore_errors=True)
