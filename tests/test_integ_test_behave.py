# -*- encoding: utf-8 -*-

import os
import shutil
import sys

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
    },
    {
        "from": "alpine:3.9",
        "name": "image",
        "version": "slimmed",
        "labels": [{"name": "foo", "value": "bar"}, {"name": "labela", "value": "a"}],
        "envs": [{"name": "baz", "value": "qux"}, {"name": "enva", "value": "a"}],
        "run": {"cmd": ["tail", "-f", "/dev/null"]},
    },
]


@pytest.fixture(scope="function", name="build_image", params=image_descriptors)
def fixture_build_image(tmpdir, request):
    def _build_image(overrides=None):
        image_descriptor = request.param
        image_dir = tmpdir.mkdir("tmp-cekit-test")

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
    feature = """@test @image
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


@pytest.mark.skipif(
    os.path.exists("/var/run/docker.sock") is False, reason="No Docker available"
)
def test_execute_simple_behave_test_with_inclusion(build_image):
    feature = """@test @image
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
            cli,
            ["-v", "test", "behave", "--include-re", "basic.feature"],
            catch_exceptions=False,
        )

    sys.stdout.write("\n")
    sys.stdout.write(result.output)

    assert result.exit_code == 0
    assert "1 feature passed, 0 failed, 0 skipped" in result.output
    assert "1 scenario passed, 0 failed, 0 skipped" in result.output
    assert "3 steps passed, 0 failed, 0 skipped, 0 undefined" in result.output


@pytest.mark.skipif(
    os.path.exists("/var/run/docker.sock") is False, reason="No Docker available"
)
def test_execute_simple_behave_test_with_exclusion(build_image):
    feature = """@test @image
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
            cli,
            ["-v", "test", "behave", "--exclude-re", "basic.feature"],
            catch_exceptions=False,
        )

    sys.stdout.write("\n")
    sys.stdout.write(result.output)

    assert result.exit_code == 0
    assert "0 features passed, 0 failed, 0 skipped" in result.output
    assert "0 scenarios passed, 0 failed, 0 skipped" in result.output
    assert "0 steps passed, 0 failed, 0 skipped, 0 undefined" in result.output


@pytest.mark.skipif(
    os.path.exists("/var/run/docker.sock") is False, reason="No Docker available"
)
def test_execute_behave_test_from_module(tmpdir):
    # given: (image is built)
    image_dir = os.path.join(tmpdir, "tmp-cekit-test")

    shutil.copytree(
        os.path.join(os.path.dirname(__file__), "images", "module-tests"), image_dir
    )

    with Chdir(image_dir):
        build_result = CliRunner().invoke(
            cli, ["-v", "build", "docker"], catch_exceptions=False
        )

    sys.stdout.write("\n")
    sys.stdout.write(build_result.output)

    assert build_result.exit_code == 0

    # when: tests are run
    with Chdir(image_dir):
        test_result = CliRunner().invoke(
            cli, ["-v", "test", "behave"], catch_exceptions=False
        )

    sys.stdout.write("\n")
    sys.stdout.write(test_result.output)

    # then:
    assert test_result.exit_code == 0
    assert "1 feature passed, 0 failed, 0 skipped" in test_result.output
    assert "1 scenario passed, 0 failed, 0 skipped" in test_result.output
    assert "2 steps passed, 0 failed, 0 skipped, 0 undefined" in test_result.output


@pytest.mark.skipif(
    os.path.exists("/var/run/docker.sock") is False, reason="No Docker available"
)
def test_simple_image_test(build_image):
    image_dir = build_image()

    shutil.copytree(
        os.path.join(os.path.dirname(__file__), "modules"),
        os.path.join(image_dir, "tests", "modules"),
    )

    feature_files = os.path.join(image_dir, "tests", "features", "test.feature")

    os.makedirs(os.path.dirname(feature_files))

    feature_label_test = """
    @test @image
    Feature: Test test

      Scenario: Check label foo
        When container is started as uid 0 with process sleep
        then the image should contain label foo with value bar
    """

    with open(feature_files, "w") as fd:
        fd.write(feature_label_test)

    with Chdir(image_dir):
        test_result = CliRunner().invoke(
            cli,
            ["-v", "test", "--image", "test/image:1.0", "behave"],
            catch_exceptions=False,
        )

    sys.stdout.write("\n")
    sys.stdout.write(test_result.output)

    # then:
    assert test_result.exit_code == 0
    assert "1 feature passed, 0 failed, 0 skipped" in test_result.output
    assert "1 scenario passed, 0 failed, 0 skipped" in test_result.output
    assert "2 steps passed, 0 failed, 0 skipped, 0 undefined" in test_result.output
    assert os.path.exists(os.path.join(image_dir, "target", "image", "Dockerfile"))


@pytest.mark.skipif(
    os.path.exists("/var/run/docker.sock") is False, reason="No Docker available"
)
def test_execute_simple_behave_test_with_env(build_image):
    feature = """@test @image
Feature: Basic tests

  Scenario: Check env
    When container is started with env
  | variable                         | value                                                        |
      | RESOURCE_ADAPTERS                | TEST_1                                                       |
      | TEST_1_ID                        | fileQS                                                       |
      | TEST_1_MODULE_SLOT               | main                                                         |
      | TEST_1_MODULE_ID                 | org.jboss.teiid.resource-adapter.file                        |
      | TEST_1_CONNECTION_CLASS          | org.teiid.resource.adapter.file.FileManagedConnectionFactory |
      | TEST_1_CONNECTION_JNDI           | java:/marketdata-file                                        |
      | TEST_1_PROPERTY_ParentDirectory  | /home/jboss/source/injected/injected-files/data              |
      | TEST_1_PROPERTY_AllowParentPaths | true                                                         |
      | TEST_1_POOL_MIN_SIZE             | 1                                                            |
      | TEST_1_POOL_MAX_SIZE             | 5                                                            |
      | TEST_1_POOL_PREFILL              | false                                                        |
      | TEST_1_POOL_FLUSH_STRATEGY       | EntirePool                                                   |
      | TEST_1_TRACKING                  | false                                                        |
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
    assert "1 step passed, 0 failed, 0 skipped, 0 undefined" in result.output
    assert (
        "Creating docker container with arguments and image: -e RESOURCE_ADAPTERS=TEST_1 -e TEST_1_ID=fileQS -e "
        "TEST_1_MODULE_SLOT=main -e TEST_1_MODULE_ID=org.jboss.teiid.resource-adapter.file -e "
        "TEST_1_CONNECTION_CLASS=org.teiid.resource.adapter.file.FileManagedConnectionFactory -e "
        "TEST_1_CONNECTION_JNDI=java:/marketdata-file -e "
        "TEST_1_PROPERTY_ParentDirectory=/home/jboss/source/injected/injected-files/data -e "
        "TEST_1_PROPERTY_AllowParentPaths=true -e TEST_1_POOL_MIN_SIZE=1 -e TEST_1_POOL_MAX_SIZE=5 -e "
        "TEST_1_POOL_PREFILL=false -e TEST_1_POOL_FLUSH_STRATEGY=EntirePool -e TEST_1_TRACKING=false "
        in result.output
    )
