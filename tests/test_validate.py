import logging
import os
import platform
import re
import shutil
import sys
import uuid
from urllib.request import Request

import pytest
import yaml
from click.testing import CliRunner

from cekit.cli import cli
from cekit.config import Config
from cekit.descriptor import Repository
from cekit.generator import base
from cekit.tools import Chdir

odcs_fake_resp = b"""Result:
{u'arches': u'x86_64',
 u'flags': [],
 u'id': 2019,
 u'koji_event': None,
 u'koji_task_id': None,
 u'owner': u'dbecvari',
 u'packages': None,
 u'removed_by': None,
 u'result_repo': u'http://hidden/compose/Temporary',
 u'result_repofile': u'http://hidden/Temporary/odcs-2019.repo',
 u'results': [u'repository'],
 u'sigkeys': u'FD431D51',
 u'source': u'rhel-7-server-rpms',
 u'source_type': 4,
 u'state': 2,
 u'state_name': u'done',
 u'state_reason': u'Compose is generated successfully',
 u'time_done': u'2018-05-02T14:11:19Z',
 u'time_removed': None,
 u'time_submitted': u'2018-05-02T14:11:16Z',
 u'time_to_expire': u'2018-05-03T14:11:16Z'}"""

image_descriptor = {
    "schema_version": 1,
    "from": "centos:7",
    "name": "test/image",
    "version": "1.0",
    "labels": [
        {"name": "foo", "value": "bar"},
        {"name": "labela", "value": "a", "description": "my description"},
    ],
    "run": {"cmd": ["sleep", "60"]},
    "modules": {
        "repositories": [{"name": "modules", "path": "tests/modules/repo_1"}],
        "install": [{"name": "foo"}],
    },
}

simple_image_descriptor = {
    "schema_version": 1,
    "from": "centos:7",
    "name": "test/image",
    "version": "1.0",
}

feature_label_test_overriden = """
@test
Feature: Test test

  Scenario: Check label foo
    When container is started as uid 0 with process sleep
    then the image should contain label foo with value overriden
"""


def run_cekit_cs_overrides(image_dir, mocker, overrides_descriptor):
    mocker.patch.object(Repository, "fetch")

    copy_repos(image_dir)

    with open(os.path.join(image_dir, "config"), "w") as fd:
        fd.write("[common]\n")
        fd.write("redhat = True")

    img_desc = image_descriptor.copy()

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    with open(os.path.join(image_dir, "overrides.yaml"), "w") as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    return run_cekit(
        image_dir,
        [
            "-v",
            "--config",
            "config",
            "build",
            "--dry-run",
            "--overrides-file",
            "overrides.yaml",
            "podman",
        ],
    )


def test_content_sets_file_container_file(tmpdir, mocker, caplog):
    # Do not try to validate dependencies while running tests, these are not necessary
    mocker.patch("cekit.generator.docker.DockerGenerator.dependencies").return_value({})
    mocker.patch("odcs.client.odcs.ODCS.new_compose", return_value={"id": 12})
    mocker.patch(
        "odcs.client.odcs.ODCS.wait_for_compose",
        return_value={"state": 2, "result_repofile": "url"},
    )
    overrides_descriptor = {
        "schema_version": 1,
        "packages": {"content_sets_file": "content_sets.yml"},
        "osbs": {"configuration": {"container_file": "container.yaml"}},
    }

    content_sets = {"x86_64": ["aaa", "bbb"]}
    container = {"compose": {"pulp_repos": True}}

    image_dir = str(tmpdir.mkdir("source"))

    with open(os.path.join(image_dir, "content_sets.yml"), "w") as fd:
        yaml.dump(content_sets, fd, default_flow_style=False)

    with open(os.path.join(image_dir, "container.yaml"), "w") as fd:
        yaml.dump(container, fd, default_flow_style=False)

    run_cekit_cs_overrides(image_dir, mocker, overrides_descriptor)

    assert (
        "Requesting ODCS pulp compose for 'aaa bbb' repositories with '[]' flags..."
        in caplog.text
    )
    assert "Waiting for compose 12 to finish..." in caplog.text
    assert "Compose finished successfully" in caplog.text
    assert (
        "The image has ContentSets repositories specified, all other repositories are removed!"
        in caplog.text
    )


def test_content_sets_file_container_embedded(tmpdir, mocker, caplog):
    # Do not try to validate dependencies while running tests, these are not necessary
    mocker.patch("cekit.generator.docker.DockerGenerator.dependencies").return_value({})
    mocker.patch("odcs.client.odcs.ODCS.new_compose", return_value={"id": 12})
    mocker.patch(
        "odcs.client.odcs.ODCS.wait_for_compose",
        return_value={"state": 2, "result_repofile": "url"},
    )
    overrides_descriptor = {
        "schema_version": 1,
        "packages": {"content_sets_file": "content_sets.yml"},
        "osbs": {"configuration": {"container": {"compose": {"pulp_repos": True}}}},
    }

    content_sets = {"x86_64": ["aaa", "bbb"]}

    image_dir = str(tmpdir.mkdir("source"))

    with open(os.path.join(image_dir, "content_sets.yml"), "w") as fd:
        yaml.dump(content_sets, fd, default_flow_style=False)

    run_cekit_cs_overrides(image_dir, mocker, overrides_descriptor)

    assert (
        "Requesting ODCS pulp compose for 'aaa bbb' repositories with '[]' flags..."
        in caplog.text
    )
    assert "Waiting for compose 12 to finish..." in caplog.text
    assert "Compose finished successfully" in caplog.text
    assert (
        "The image has ContentSets repositories specified, all other repositories are removed!"
        in caplog.text
    )


def test_content_sets_embedded_container_embedded(tmpdir, mocker, caplog):
    mocker.patch("odcs.client.odcs.ODCS.new_compose", return_value={"id": 12})
    mocker.patch(
        "odcs.client.odcs.ODCS.wait_for_compose",
        return_value={"state": 2, "result_repofile": "url"},
    )
    overrides_descriptor = {
        "schema_version": 1,
        "packages": {"content_sets": {"x86_64": ["aaa", "bbb"]}},
        "osbs": {"configuration": {"container": {"compose": {"pulp_repos": True}}}},
    }

    image_dir = str(tmpdir.mkdir("source"))

    run_cekit_cs_overrides(image_dir, mocker, overrides_descriptor)

    assert (
        "Required CEKit library 'odcs-client' was found as a 'odcs' module!"
        in caplog.text
    )
    assert (
        "Requesting ODCS pulp compose for 'aaa bbb' repositories with '[]' flags..."
        in caplog.text
    )
    assert "Waiting for compose 12 to finish..." in caplog.text
    assert "Compose finished successfully" in caplog.text
    assert (
        "The image has ContentSets repositories specified, all other repositories are removed!"
        in caplog.text
    )


def test_content_sets_embedded_container_file(tmpdir, mocker, caplog):
    # Do not try to validate dependencies while running tests, these are not necessary
    mocker.patch("cekit.generator.docker.DockerGenerator.dependencies").return_value({})
    mocker.patch("odcs.client.odcs.ODCS.new_compose", return_value={"id": 12})
    mocker.patch(
        "odcs.client.odcs.ODCS.wait_for_compose",
        return_value={"state": 2, "result_repofile": "url"},
    )

    overrides_descriptor = {
        "schema_version": 1,
        "packages": {"content_sets": {"x86_64": ["aaa", "bbb"]}},
        "osbs": {"configuration": {"container_file": "container.yaml"}},
    }

    image_dir = str(tmpdir.mkdir("source"))
    container = {"compose": {"pulp_repos": True}}

    with open(os.path.join(image_dir, "container.yaml"), "w") as fd:
        yaml.dump(container, fd, default_flow_style=False)

    run_cekit_cs_overrides(image_dir, mocker, overrides_descriptor)

    assert (
        "Requesting ODCS pulp compose for 'aaa bbb' repositories with '[]' flags..."
        in caplog.text
    )
    assert "Waiting for compose 12 to finish..." in caplog.text
    assert "Compose finished successfully" in caplog.text
    assert (
        "The image has ContentSets repositories specified, all other repositories are removed!"
        in caplog.text
    )


def copy_repos(dst):
    shutil.copytree(
        os.path.join(os.path.dirname(__file__), "modules"),
        os.path.join(dst, "tests", "modules"),
    )


def test_simple_image_build(tmpdir):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    run_cekit(image_dir, ["-v", "build", "podman"])


def test_image_generate_with_multiple_overrides(tmpdir):
    override1 = "{'labels': [{'name': 'foo', 'value': 'bar'}]}"

    override2 = "{'labels': [{'name': 'foo', 'value': 'baz'}]}"

    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    overrides_descriptor = {
        "schema_version": 1,
        "modules": {
            "repositories": [{"name": "modules", "path": "tests/modules/repo_2"}]
        },
    }

    with open(os.path.join(image_dir, "overrides.yaml"), "w") as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    run_cekit(
        image_dir,
        [
            "-v",
            "build",
            "--overrides",
            override1,
            "--overrides",
            override2,
            "--dry-run",
            "podman",
        ],
    )

    effective_image = {}
    with open(os.path.join(image_dir, "target", "image.yaml"), "r") as file_:
        effective_image = yaml.safe_load(file_)

    assert {"name": "foo", "value": "baz"} in effective_image["labels"]


@pytest.mark.skipif(
    platform.system() == "Darwin", reason="Disabled on macOS, cannot run Docker"
)
@pytest.mark.skipif(
    os.path.exists("/var/run/docker.sock") is False, reason="No Docker available"
)
def test_image_test_with_override(tmpdir):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    feature_files = os.path.join(image_dir, "tests", "features", "test.feature")

    os.makedirs(os.path.dirname(feature_files))

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    overrides_descriptor = {"labels": [{"name": "foo", "value": "overriden"}]}

    with open(os.path.join(image_dir, "overrides.yaml"), "w") as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    with open(feature_files, "w") as fd:
        fd.write(feature_label_test_overriden)

    run_cekit(
        image_dir, ["-v", "build", "--overrides-file", "overrides.yaml", "docker"]
    )

    with open(os.path.join(image_dir, "target", "image.yaml"), "r") as file_:
        effective_image = yaml.safe_load(file_)

    assert {"name": "foo", "value": "overriden"} in effective_image["labels"]

    run_cekit(image_dir, ["-v", "test", "--image", "test/image:1.0", "behave"])


@pytest.mark.skipif(
    platform.system() == "Darwin", reason="Disabled on macOS, cannot run Docker"
)
@pytest.mark.skipif(
    os.path.exists("/var/run/docker.sock") is False, reason="No Docker available"
)
def test_image_test_with_multiple_overrides(tmpdir):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    feature_files = os.path.join(image_dir, "tests", "features", "test.feature")

    os.makedirs(os.path.dirname(feature_files))

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    overrides_descriptor = {"labels": [{"name": "foo", "value": "X"}]}

    with open(os.path.join(image_dir, "overrides.yaml"), "w") as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    overrides_descriptor2 = {"labels": [{"name": "foo", "value": "Y"}]}

    with open(os.path.join(image_dir, "overrides2.yaml"), "w") as fd:
        yaml.dump(overrides_descriptor2, fd, default_flow_style=False)

    with open(feature_files, "w") as fd:
        fd.write(feature_label_test_overriden)

    run_cekit(
        image_dir,
        [
            "-v",
            "build",
            "--overrides-file",
            "overrides.yaml",
            "--overrides-file",
            "overrides2.yaml",
            "--overrides",
            "{'labels': [{'name': 'foo', 'value': 'overriden'}]}",
            "docker",
        ],
    )

    effective_image = {}
    with open(os.path.join(image_dir, "target", "image.yaml"), "r") as file_:
        effective_image = yaml.safe_load(file_)

    assert {"name": "foo", "value": "overriden"} in effective_image["labels"]

    run_cekit(image_dir, ["-v", "test", "--image", "test/image:1.0", "behave"])


@pytest.mark.skipif(
    platform.system() == "Darwin", reason="Disabled on macOS, cannot run Docker"
)
@pytest.mark.skipif(
    os.path.exists("/var/run/docker.sock") is False, reason="No Docker available"
)
def test_image_test_with_override_on_cmd(tmpdir):
    overrides_descriptor = "{'labels': [{'name': 'foo', 'value': 'overriden'}]}"

    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    feature_files = os.path.join(image_dir, "tests", "features", "test.feature")

    os.makedirs(os.path.dirname(feature_files))

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    with open(feature_files, "w") as fd:
        fd.write(feature_label_test_overriden)

    run_cekit(image_dir, ["-v", "build", "--overrides", overrides_descriptor, "docker"])

    run_cekit(image_dir, ["-v", "test", "--image", "test/image:1.0", "behave"])


def test_image_test_with_override_yaml_on_cmd(tmpdir):
    overrides_descriptor = """labels:
  - name: foo
    value: overriden
"""

    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    feature_files = os.path.join(image_dir, "tests", "features", "test.feature")

    os.makedirs(os.path.dirname(feature_files))

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    with open(feature_files, "w") as fd:
        fd.write(feature_label_test_overriden)

    run_cekit(
        image_dir,
        ["-v", "build", "--overrides", overrides_descriptor, "--dry-run", "podman"],
    )
    with open(
        os.path.join(image_dir, "target", "image", "Containerfile"), "r"
    ) as _file:
        dockerfile = _file.read()
    assert (
        """LABEL \\
            foo="overriden"""
        in dockerfile
    )


def test_module_override(tmpdir):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    overrides_descriptor = {
        "schema_version": 1,
        "envs": [
            {"name": "not-there", "description": "my-description"},
            {"name": "foobar", "value": "dummy"},
        ],
        "modules": {
            "repositories": [{"name": "modules", "path": "tests/modules/repo_2"}]
        },
    }

    with open(os.path.join(image_dir, "overrides.yaml"), "w") as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    run_cekit(
        image_dir,
        ["-v", "build", "--dry-run", "--overrides-file", "overrides.yaml", "podman"],
    )

    module_dir = os.path.join(image_dir, "target", "image", "modules", "foo")

    assert os.path.exists(os.path.join(module_dir, "overriden"))

    assert not os.path.exists(os.path.join(module_dir, "original"))
    assert not check_dockerfile_text(image_dir, "not-there", "Containerfile")
    assert check_dockerfile(image_dir, 'foobar="dummy"', "Containerfile")
    assert check_dockerfile(
        image_dir, 'RUN [ "sh", "-x", "/tmp/scripts/foo/script" ]', "Containerfile"
    )


# https://github.com/cekit/cekit/issues/489
def test_override_add_module_and_packages_in_overrides(tmpdir):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(simple_image_descriptor, fd, default_flow_style=False)

    overrides_descriptor = {
        "schema_version": 1,
        "modules": {
            "repositories": [{"name": "modules", "path": "tests/modules/repo_3"}]
        },
    }

    with open(os.path.join(image_dir, "overrides.yaml"), "w") as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    run_cekit(
        image_dir,
        [
            "-v",
            "build",
            "--dry-run",
            "--overrides-file",
            "overrides.yaml",
            "--overrides",
            '{"modules": {"install": [{"name": "main"}, {"name": "child"}] } }',
            "--overrides",
            '{"packages": {"install": ["package1", "package2"] } }',
            "--overrides",
            '{"artifacts": [{"name": "test", "path": "image.yaml", "dest": "/tmp/artifacts/"}] }',
            "podman",
        ],
    )

    assert check_dockerfile(
        image_dir,
        "RUN yum --setopt=tsflags=nodocs install -y package1 package2 \\",
        "Containerfile",
    )
    assert check_dockerfile(
        image_dir, 'RUN [ "sh", "-x", "/tmp/scripts/main/script_a" ]', "Containerfile"
    )
    assert check_dockerfile_text(
        image_dir,
        "        COPY \\\n            test \\\n            /tmp/artifacts/",
        "Containerfile",
    )


# Test work of workaround for https://bugzilla.redhat.com/show_bug.cgi?id=1700341
def test_microdnf_clean_all_cmd_present(tmpdir):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    overrides_descriptor = {"schema_version": 1, "packages": {"manager": "microdnf"}}

    with open(os.path.join(image_dir, "overrides.yaml"), "w") as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    run_cekit(
        image_dir,
        [
            "-v",
            "build",
            "--dry-run",
            "--overrides-file",
            "overrides.yaml",
            "--overrides",
            '{"packages": {"install": ["package1", "package2"] } }',
            "podman",
        ],
    )

    required_matches = [
        "RUN microdnf --setopt=install_weak_deps=0 --setopt=tsflags=nodocs install -y package1 package2 \\",
        "&& microdnf clean all \\",
        "&& rpm -q package1 package2",
    ]

    for match in required_matches:
        assert check_dockerfile(image_dir, match, "Containerfile")


def check_dockerfile(image_dir, match, container_file="Dockerfile"):
    with open(os.path.join(image_dir, "target", "image", container_file), "r") as fd:
        for line in fd.readlines():
            if line.strip() == match.strip():
                return True
    return False


def check_dockerfile_text(image_dir, match, container_file="Dockerfile"):
    with open(os.path.join(image_dir, "target", "image", container_file), "r") as fd:
        dockerfile = fd.read()
        print(f"MATCH:\n{match}")
        print(f"DOCKERFILE:\n{dockerfile}")
        if match in dockerfile:
            return True
    return False


def regex_dockerfile(image_dir, exp_regex, container_file="Dockerfile"):
    with open(os.path.join(image_dir, "target", "image", container_file), "r") as fd:
        dockerfile_content = fd.read()
        regex = re.compile(exp_regex, re.MULTILINE)
        assert regex.search(dockerfile_content) is not None


def check_dockerfile_uniq(image_dir, match, container_file="Dockerfile"):
    found = False
    with open(os.path.join(image_dir, "target", "image", container_file), "r") as fd:
        for line in fd.readlines():
            if line.strip() == match.strip():
                if found:
                    return False
                else:
                    found = True
    return found


def test_local_module_not_injected(tmpdir):
    image_dir = str(tmpdir.mkdir("source"))

    local_desc = image_descriptor.copy()
    local_desc.pop("modules")

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(local_desc, fd, default_flow_style=False)

    shutil.copytree(
        os.path.join(os.path.dirname(__file__), "modules", "repo_1"),
        os.path.join(image_dir, "modules"),
    )
    run_cekit(image_dir)
    assert not os.path.exists(os.path.join(image_dir, "target", "image", "modules"))


def test_run_override_user(tmpdir):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    overrides_descriptor = {"schema_version": 1, "run": {"user": "4321"}}

    with open(os.path.join(image_dir, "overrides.yaml"), "w") as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    run_cekit(
        image_dir,
        ["-v", "build", "--dry-run", "--overrides-file", "overrides.yaml", "podman"],
    )

    assert check_dockerfile(image_dir, "USER 4321", "Containerfile")


def get_res(mocker):
    res = mocker.Mock()
    res.getcode.return_value = 200
    res.read.side_effect = [b"{'run': {'user': '4321'}}", None]
    res.getheader.return_value = 0
    return res


def test_run_load_remote_override(tmpdir, mocker):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    config = Config()
    config.cfg["common"] = {}
    mock_urlopen = mocker.patch("cekit.tools.urlopen", return_value=get_res(mocker))

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    run_cekit(
        image_dir,
        [
            "-v",
            "build",
            "--dry-run",
            "--overrides-file",
            "https://example.com/overrides.yaml",
            "podman",
        ],
    )

    assert check_dockerfile(image_dir, "USER 4321", "Containerfile")
    request: Request = mock_urlopen.call_args[0][0]
    assert request.get_full_url() == "https://example.com/overrides.yaml"


def test_run_load_remote_file_override(tmpdir, mocker):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    config = Config()
    config.cfg["common"] = {}

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    overrides_descriptor = {"schema_version": 1, "run": {"user": "4321"}}

    with open(os.path.join(image_dir, "remote_overrides.yaml"), "w") as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    run_cekit(
        image_dir,
        [
            "-v",
            "build",
            "--dry-run",
            "--overrides-file",
            "file://" + image_dir + "/remote_overrides.yaml",
            "podman",
        ],
    )

    assert check_dockerfile(image_dir, "USER 4321", "Containerfile")


def test_run_override_artifact(tmpdir):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, "bar.jar"), "w") as fd:
        fd.write("foo")

    img_desc = image_descriptor.copy()
    img_desc["artifacts"] = [{"url": "https://foo/bar.jar"}]

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    overrides_descriptor = {"schema_version": 1, "artifacts": [{"path": "bar.jar"}]}

    with open(os.path.join(image_dir, "overrides.yaml"), "w") as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    run_cekit(
        image_dir,
        ["-v", "build", "--dry-run", "--overrides-file", "overrides.yaml", "podman"],
    )

    assert check_dockerfile_uniq(image_dir, "bar.jar \\", "Containerfile")


def test_run_override_artifact_with_custom_original_destination(tmpdir):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, "bar.jar"), "w") as fd:
        fd.write("foo")

    img_desc = image_descriptor.copy()
    img_desc["artifacts"] = [{"url": "https://foo/bar.jar", "dest": "/tmp/destination"}]

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    overrides_descriptor = {"schema_version": 1, "artifacts": [{"path": "bar.jar"}]}

    with open(os.path.join(image_dir, "overrides.yaml"), "w") as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    run_cekit(
        image_dir,
        ["-v", "build", "--dry-run", "--overrides-file", "overrides.yaml", "podman"],
    )

    assert (
        check_dockerfile_text(
            image_dir, "/tmp/artifacts/' destination", "Containerfile"
        )
        is False
    )
    assert check_dockerfile_text(
        image_dir, "/tmp/destination/' destination", "Containerfile"
    )
    assert check_dockerfile_uniq(image_dir, "bar.jar \\", "Containerfile")


def test_run_override_artifact_with_custom_override_destination(tmpdir):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, "bar.jar"), "w") as fd:
        fd.write("foo")

    img_desc = image_descriptor.copy()
    img_desc["artifacts"] = [{"url": "https://foo/bar.jar"}]

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    overrides_descriptor = {
        "schema_version": 1,
        "artifacts": [{"path": "bar.jar", "dest": "/tmp/new-destination/"}],
    }

    with open(os.path.join(image_dir, "overrides.yaml"), "w") as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    run_cekit(
        image_dir,
        ["-v", "build", "--dry-run", "--overrides-file", "overrides.yaml", "podman"],
    )

    assert (
        check_dockerfile_text(
            image_dir, "/tmp/destination/' destination", "Containerfile"
        )
        is False
    )
    assert check_dockerfile_text(
        image_dir, "/tmp/new-destination/' destination", "Containerfile"
    )
    assert check_dockerfile_uniq(image_dir, "bar.jar \\", "Containerfile")


def test_run_override_artifact_with_custom_override_example1(tmpdir, mocker, caplog):
    # Ignore checksum verification.
    mocker.patch("cekit.crypto.get_sum", return_value="123456")
    mocker.patch("cekit.cache.artifact.get_sum", return_value="123456")

    cache_id = uuid.uuid4()
    mocker.patch("uuid.uuid4", return_value=cache_id)

    work_dir = str(tmpdir.mkdir("work_dir"))
    image_dir = str(tmpdir.mkdir("source"))
    os.makedirs(work_dir + "/cache")

    with open(os.path.join(image_dir, "bar2222.jar"), "w") as fd:
        fd.write("foo")

    copy_repos(image_dir)

    with open(os.path.join(image_dir, "config"), "w") as fd:
        fd.write("[common]\n")
        fd.write("cache_url = #filename#\n")
        fd.write("work_dir = " + work_dir + "\n")

    with open(os.path.join(work_dir, "cache", str(cache_id)), "w") as fd:
        fd.write("jar-content")

    img_desc = image_descriptor.copy()
    img_desc["artifacts"] = [
        {
            "name": "bar.jar",
            "url": "https://dummy.com/bar-url.jar",
            "dest": "/tmp/destination",
            "target": "original-bar.jar",
            "description": "original-description",
        }
    ]

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    overrides_descriptor = {
        "schema_version": 1,
        "artifacts": [{"name": "bar.jar", "md5": "123456", "target": "bar2222.jar"}],
    }

    with open(os.path.join(image_dir, "overrides.yaml"), "w") as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    run_cekit(
        image_dir,
        [
            "-v",
            "--config",
            "config",
            "build",
            "--dry-run",
            "--overrides-file",
            "overrides.yaml",
            "podman",
        ],
    )

    with open(
        os.path.join(str(tmpdir), "source", "target", "image", "Containerfile"), "r"
    ) as _file:
        dockerfile = _file.read()
    assert "/tmp/destination/' destination" in dockerfile
    assert (
        "Final (with override) artifact is [('description', 'original-description'), ('dest', '/tmp/destination/'), ('md5', '123456'), "
        "('name', 'bar.jar'), ('target', 'bar2222.jar')]" in caplog.text
    )


def test_run_override_artifact_with_custom_override_example2(tmpdir, mocker, caplog):
    # Ignore checksum verification.
    mocker.patch("cekit.crypto.get_sum", return_value="123456")
    mocker.patch("cekit.cache.artifact.get_sum", return_value="123456")

    cache_id = uuid.uuid4()
    mocker.patch("uuid.uuid4", return_value=cache_id)

    work_dir = str(tmpdir.mkdir("work_dir"))
    image_dir = str(tmpdir.mkdir("source"))
    os.makedirs(work_dir + "/cache")

    copy_repos(image_dir)

    with open(os.path.join(image_dir, "config"), "w") as fd:
        fd.write("[common]\n")
        fd.write("cache_url = #filename#\n")

    with open(os.path.join(image_dir, "bar.jar"), "w") as fd:
        fd.write("jar-content")

    img_desc = image_descriptor.copy()
    img_desc["artifacts"] = [
        {
            "name": "bar.jar",
            "url": "https://dummy.com/bar-url.jar",
            "dest": "/tmp/destination",
            "target": "original-bar.jar",
            "description": "original-description",
        }
    ]

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    overrides_descriptor = {
        "schema_version": 1,
        "artifacts": [
            {"name": "bar.jar", "md5": "123456", "description": "new-description"},
            {"name": "foobar.jar", "url": "https://dummy.com/foobar.jar"},
        ],
    }

    with open(os.path.join(image_dir, "overrides.yaml"), "w") as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    run_cekit(
        image_dir,
        [
            "-v",
            "--config",
            "config",
            "build",
            "--dry-run",
            "--overrides-file",
            "overrides.yaml",
            "podman",
        ],
    )

    with open(
        os.path.join(str(tmpdir), "source", "target", "image", "Containerfile"), "r"
    ) as _file:
        dockerfile = _file.read()
    assert "/tmp/destination/' destination" in dockerfile
    assert (
        "Final (with override) artifact is [('description', 'new-description'), ('dest', '/tmp/destination/'), "
        "('md5', '123456'), ('name', 'bar.jar'), ('target', 'original-bar.jar')]"
        in caplog.text
    )
    assert (
        "Final (with override) artifact is [('dest', '/tmp/artifacts/'), ('name', 'foobar.jar'), "
        "('target', 'foobar.jar'), ('url', 'https://dummy.com/foobar.jar')]"
        in caplog.text
    )


def test_run_path_artifact_brew(tmpdir, caplog):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)
    with open(os.path.join(image_dir, "bar.jar"), "w") as fd:
        fd.write("foo")

    img_desc = image_descriptor.copy()
    img_desc["artifacts"] = [
        {
            "name": "aaa",
            "md5": "d41d8cd98f00b204e9800998ecf84271",
            "target": "target_foo",
        }
    ]

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    run_cekit_exception(image_dir)

    assert (
        "Cekit is not able to fetch resource 'aaa' automatically. Please use cekit-cache command to add this artifact manually."
        in caplog.text
    )


def test_run_path_artifact_target(tmpdir):
    image_dir = str(tmpdir.mkdir("source"))

    copy_repos(image_dir)

    with open(os.path.join(image_dir, "bar.jar"), "w") as fd:
        fd.write("foo")

    img_desc = image_descriptor.copy()
    img_desc["artifacts"] = [{"path": "bar.jar", "target": "target_foo"}]

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    run_cekit(image_dir)

    assert check_dockerfile_uniq(image_dir, "target_foo \\")


def test_run_alpine(tmpdir):
    image_dir = str(tmpdir.mkdir("source"))

    copy_repos(image_dir)

    with open(os.path.join(image_dir, "bar.jar"), "w") as fd:
        fd.write("foo")

    img_desc = image_descriptor.copy()
    img_desc["from"] = "alpine:3.10"
    img_desc["packages"] = {"install": ["python3"], "manager": "apk"}

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    run_cekit(
        image_dir, parameters=["-v", "build", "podman"], env={"BUILDAH_LAYERS": "false"}
    )


def test_run_debian_slim(tmpdir):
    image_dir = str(tmpdir.mkdir("source"))

    copy_repos(image_dir)

    with open(os.path.join(image_dir, "bar.jar"), "w") as fd:
        fd.write("foo")

    img_desc = image_descriptor.copy()
    img_desc["from"] = "debian:stable-slim"
    img_desc["packages"] = {"install": ["python3-minimal"], "manager": "apt-get"}

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    run_cekit(
        image_dir, parameters=["-v", "build", "podman"], env={"BUILDAH_LAYERS": "false"}
    )


def test_execution_order(tmpdir):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    img_desc = image_descriptor.copy()
    img_desc["modules"]["install"] = [{"name": "main"}]
    img_desc["modules"]["repositories"] = [
        {"name": "modules", "path": "tests/modules/repo_3"}
    ]

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    run_cekit(image_dir)

    expected_modules_order = """
###### START module 'child_of_child:1.0'
###### \\
        # Copy 'child_of_child' module content
        COPY modules/child_of_child /tmp/scripts/child_of_child
        # Set 'child_of_child' module defined environment variables
        ENV \\
            foo="child_of_child"
        # Custom scripts from 'child_of_child' module
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/child_of_child/script_d" ]
###### /
###### END module 'child_of_child:1.0'

###### START module 'child2_of_child:1.0'
###### \\
        # Copy 'child2_of_child' module content
        COPY modules/child2_of_child /tmp/scripts/child2_of_child
        # Custom scripts from 'child2_of_child' module
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/child2_of_child/scripti_e" ]
###### /
###### END module 'child2_of_child:1.0'

###### START module 'child3_of_child:1.0'
###### \\
        # Copy 'child3_of_child' module content
        COPY modules/child3_of_child /tmp/scripts/child3_of_child
        # Custom scripts from 'child3_of_child' module
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/child3_of_child/script_f" ]
###### /
###### END module 'child3_of_child:1.0'

###### START module 'child:1.0'
###### \\
        # Copy 'child' module content
        COPY modules/child /tmp/scripts/child
        # Set 'child' module defined environment variables
        ENV \\
            foo="child"
        # Custom scripts from 'child' module
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/child/script_b" ]
###### /
###### END module 'child:1.0'

###### START module 'child_2:1.0'
###### \\
        # Copy 'child_2' module content
        COPY modules/child_2 /tmp/scripts/child_2
        # Custom scripts from 'child_2' module
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/child_2/script_c" ]
###### /
###### END module 'child_2:1.0'

###### START module 'child_of_child3:1.0'
###### \\
        # Copy 'child_of_child3' module content
        COPY modules/child_of_child3 /tmp/scripts/child_of_child3
        # Custom scripts from 'child_of_child3' module
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/child_of_child3/script_g" ]
###### /
###### END module 'child_of_child3:1.0'

###### START module 'child2_of_child3:1.0'
###### \\
        # Copy 'child2_of_child3' module content
        COPY modules/child2_of_child3 /tmp/scripts/child2_of_child3
        # Custom scripts from 'child2_of_child3' module
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/child2_of_child3/script_h" ]
###### /
###### END module 'child2_of_child3:1.0'

###### START module 'child_3:1.0'
###### \\
###### /
###### END module 'child_3:1.0'

###### START module 'main:1.0'
###### \\
        # Copy 'main' module content
        COPY modules/main /tmp/scripts/main
        # Set 'main' module defined environment variables
        ENV \\
            foo="main"
        # Custom scripts from 'main' module
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/main/script_a" ]
###### /
###### END module 'main:1.0'
"""
    assert check_dockerfile_text(image_dir, expected_modules_order)


def test_override_modules_child(tmpdir, mocker):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    img_desc = image_descriptor.copy()
    img_desc["modules"]["install"] = [{"name": "main"}]
    img_desc["modules"]["repositories"] = [
        {"name": "modules", "path": "tests/modules/repo_3"}
    ]

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    run_cekit(image_dir)
    assert check_dockerfile_text(image_dir, 'foo="main"')


def test_override_modules_flat(tmpdir, mocker):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    img_desc = image_descriptor.copy()
    img_desc["modules"]["install"] = [
        {"name": "mod_1"},
        {"name": "mod_2"},
        {"name": "mod_3"},
        {"name": "mod_4"},
    ]
    img_desc["modules"]["repositories"] = [
        {"name": "modules", "path": "tests/modules/repo_4"}
    ]

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    run_cekit(image_dir)

    assert check_dockerfile_text(image_dir, 'foo="mod_2"')
    assert not check_dockerfile_text(image_dir, "RUN yum clean all")


def test_execution_order_flat(tmpdir, mocker):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    img_desc = image_descriptor.copy()
    img_desc["modules"]["install"] = [
        {"name": "mod_1"},
        {"name": "mod_2"},
        {"name": "mod_3"},
        {"name": "mod_4"},
    ]
    img_desc["modules"]["repositories"] = [
        {"name": "modules", "path": "tests/modules/repo_4"}
    ]

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    run_cekit(image_dir)

    expected_modules_order = """
###### START module 'mod_1:1.0'
###### \\
        # Copy 'mod_1' module content
        COPY modules/mod_1 /tmp/scripts/mod_1
        # Set 'mod_1' module defined environment variables
        ENV \\
            foo="mod_1"
        # Custom scripts from 'mod_1' module
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/mod_1/a" ]
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/mod_1/b" ]
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/mod_1/c" ]
###### /
###### END module 'mod_1:1.0'

###### START module 'mod_2:1.0'
###### \\
        # Copy 'mod_2' module content
        COPY modules/mod_2 /tmp/scripts/mod_2
        # Set 'mod_2' module defined environment variables
        ENV \\
            foo="mod_2"
        # Custom scripts from 'mod_2' module
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/mod_2/a" ]
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/mod_2/b" ]
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/mod_2/c" ]
###### /
###### END module 'mod_2:1.0'

###### START module 'mod_3:1.0'
###### \\
        # Copy 'mod_3' module content
        COPY modules/mod_3 /tmp/scripts/mod_3
        # Custom scripts from 'mod_3' module
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/mod_3/a" ]
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/mod_3/b" ]
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/mod_3/c" ]
###### /
###### END module 'mod_3:1.0'

###### START module 'mod_4:1.0'
###### \\
        # Copy 'mod_4' module content
        COPY modules/mod_4 /tmp/scripts/mod_4
        # Custom scripts from 'mod_4' module
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/mod_4/a" ]
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/mod_4/b" ]
        USER root
        RUN [ "sh", "-x", "/tmp/scripts/mod_4/c" ]
###### /
###### END module 'mod_4:1.0'
"""
    assert check_dockerfile_text(image_dir, expected_modules_order)
    assert not check_dockerfile_text(image_dir, "RUN yum clean all")


def test_package_related_commands_packages_in_module(tmpdir, mocker):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    img_desc = image_descriptor.copy()
    img_desc["modules"]["install"] = [
        {"name": "packages_module"},
        {"name": "packages_module_1"},
    ]
    img_desc["modules"]["repositories"] = [
        {"name": "modules", "path": "tests/modules/repo_packages"}
    ]

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    run_cekit(image_dir)

    expected_packages_order_install = """
###### START module 'packages_module:1.0'
###### \\
        # Switch to 'root' user for package management for 'packages_module' module defined packages
        USER root
        # Install packages defined in the 'packages_module' module
        RUN yum --setopt=tsflags=nodocs install -y kernel java-1.8.0-openjdk \\
            && rpm -q kernel java-1.8.0-openjdk
###### /
###### END module 'packages_module:1.0'

###### START module 'packages_module_1:1.0'
###### \\
        # Switch to 'root' user for package management for 'packages_module_1' module defined packages
        USER root
        # Install packages defined in the 'packages_module_1' module
        RUN yum --setopt=tsflags=nodocs install -y wget mc \\
            && rpm -q wget mc
###### /
###### END module 'packages_module_1:1.0'
"""

    assert check_dockerfile_text(image_dir, expected_packages_order_install)
    regex_dockerfile(image_dir, "rm -rf.*/var/cache/yum")


def test_package_related_commands_packages_in_image(tmpdir, caplog):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    img_desc = image_descriptor.copy()
    img_desc["packages"] = {"install": ["wget", "mc"]}

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    run_cekit(
        image_dir,
        parameters=[
            "-v",
            "build",
            "--dry-run",
            "--container-file",
            "Dockerfile",
            "podman",
        ],
    )

    expected_packages_install = """
        USER root
        # Install packages defined in the 'test/image' image
        RUN yum --setopt=tsflags=nodocs install -y wget mc \\
            && rpm -q wget mc
"""

    assert (
        "Required CEKit library 'odcs-client' was found as a 'odcs' module!"
        not in caplog.text
    )
    assert check_dockerfile_text(image_dir, expected_packages_install)


def test_nonexisting_image_descriptor(mocker, tmpdir, caplog):
    image_dir = str(tmpdir.mkdir("source"))

    run_cekit_exception(
        image_dir, ["-v", "--descriptor", "nonexisting.yaml", "build", "podman"]
    )

    assert (
        "Descriptor ('nonexisting.yaml') could not be found on the path, please check your arguments!"
        in caplog.text
    )


def test_nonexisting_override_file(mocker, tmpdir, caplog):
    image_dir = str(tmpdir.mkdir("source"))
    img_desc = image_descriptor.copy()

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    run_cekit_exception(
        image_dir,
        ["-v", "build", "--dry-run", "--overrides-file", "nonexisting.yaml", "podman"],
    )

    assert "Loading override 'nonexisting.yaml'" in caplog.text
    assert (
        "Descriptor ('nonexisting.yaml') could not be found on the path, please check your arguments!"
        in caplog.text
    )


def test_incorrect_override_file(mocker, tmpdir, caplog):
    image_dir = str(tmpdir.mkdir("source"))
    img_desc = image_descriptor.copy()

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    run_cekit_exception(
        image_dir, ["-v", "build", "--dry-run", "--overrides", "{wrong!}", "podman"]
    )

    assert "Loading override '{wrong!}'" in caplog.text
    assert "Schema validation failed" in caplog.text
    assert "Key 'wrong!' was not defined" in caplog.text


@pytest.mark.skipif(
    os.path.exists("/var/run/docker.sock") is False, reason="No Docker available"
)
def test_simple_image_build_error_local_docker_socket_permission_denied(
    tmpdir, mocker, caplog
):
    mocker.patch(
        "urllib3.connectionpool.HTTPConnectionPool.urlopen",
        side_effect=PermissionError(),
    )

    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    run_cekit_exception(image_dir, ["-v", "build", "docker"])

    assert (
        "Could not connect to the Docker daemon at 'http+docker://localhost', please make sure the Docker daemon is running"
        in caplog.text
    )


@pytest.mark.skipif(
    os.path.exists("/var/run/docker.sock") is False, reason="No Docker available"
)
def test_simple_image_build_error_local_docker_stopped(tmpdir, mocker, caplog):
    mocker.patch(
        "urllib3.connectionpool.HTTPConnectionPool.urlopen",
        side_effect=FileNotFoundError(),
    )

    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    run_cekit_exception(image_dir, ["-v", "build", "docker"])

    assert (
        "Could not connect to the Docker daemon at 'http+docker://localhost', please make sure the Docker daemon is running"
        in caplog.text
    )


@pytest.mark.skipif(
    os.path.exists("/var/run/docker.sock") is False, reason="No Docker available"
)
def test_simple_image_build_error_connection_error_remote_docker_with_custom_docker_host(
    tmpdir, mocker, monkeypatch, caplog
):
    mocker.patch(
        "urllib3.connectionpool.HTTPConnectionPool.urlopen",
        side_effect=PermissionError(),
    )

    monkeypatch.setenv("DOCKER_HOST", "tcp://127.0.0.1:1234")

    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    run_cekit_exception(image_dir, ["-v", "build", "docker"])

    assert (
        "Could not connect to the Docker daemon at 'http://127.0.0.1:1234', please make sure the Docker daemon is running"
        in caplog.text
    )
    assert (
        "If Docker daemon is running, please make sure that you specified valid parameters in the 'DOCKER_HOST' environment variable, examples: 'unix:///var/run/docker.sock', 'tcp://192.168.22.33:1234'. You may also need to specify 'DOCKER_TLS_VERIFY', and 'DOCKER_CERT_PATH' environment variables"
        in caplog.text
    )


def test_proper_decoding(tmpdir, caplog):
    image_dir = str(tmpdir.mkdir("source"))

    shutil.copy2(
        os.path.join(
            os.path.dirname(__file__), "images", "image-gh-538-py27-encoding.yaml"
        ),
        os.path.join(image_dir, "image.yaml"),
    )

    run_cekit(image_dir, ["-v", "build", "podman"])

    assert "Finished!" in caplog.text


# https://github.com/cekit/cekit/issues/533
@pytest.mark.parametrize("parameter", ["content_sets", "content_sets_file"])
def test_disabling_content_sets(tmpdir, caplog, parameter):
    image_dir = str(tmpdir.mkdir("source"))

    shutil.copy2(
        os.path.join(
            os.path.dirname(__file__),
            "images",
            "image-gh-533-disable-content-sets-file.yaml",
        ),
        os.path.join(image_dir, "image.yaml"),
    )

    with open(os.path.join(image_dir, "content_sets.yml"), "w") as fd:
        yaml.dump(
            {"x86_64": ["rhel-server-rhscl-7-rpms", "rhel-7-server-rpms"]},
            fd,
            default_flow_style=False,
        )

    run_cekit(
        image_dir,
        [
            "-v",
            "build",
            "--dry-run",
            # Ugly, but double braces are required for 'format to work'
            "--overrides",
            f'{{"packages": {{"{parameter}": ~}}}}',
            "podman",
        ],
    )

    with open(os.path.join(image_dir, "target", "image.yaml"), "r") as file_:
        effective_image = yaml.safe_load(file_)

    assert "content_sets" not in effective_image["packages"]
    assert "Finished!" in caplog.text


# https://github.com/cekit/cekit/issues/551
def test_validation_of_image_and_module_descriptors(tmpdir, mocker, caplog):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    run_cekit(image_dir, ["-v", "build", "--validate", "podman"])

    assert (
        "The --validate parameter was specified, generation will not be performed, exiting"
        in caplog.text
    )


def test_color(tmpdir, mocker, caplog):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    result = run_cekit(image_dir, ["-v", "--nocolor", "build", "--validate", "podman"])

    assert "\033" not in result.output

    result = run_cekit(image_dir, ["-v", "build", "--validate", "podman"])

    assert "\033" in result.output

    result = run_cekit(
        image_dir, ["-v", "build", "--validate", "podman"], env={"NO_COLOR": "TRUE"}
    )

    assert "\033" not in result.output


# https://github.com/cekit/cekit/issues/551
def test_validation_of_image_and_module_descriptors_should_fail_on_invalid_descriptor(
    tmpdir, mocker, caplog
):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    descriptor = image_descriptor.copy()

    del descriptor["name"]

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(descriptor, fd, default_flow_style=False)

    run_cekit_exception(image_dir, ["-v", "build", "--validate", "podman"])

    assert "Cannot validate schema: Image" in caplog.text
    assert "Cannot find required key 'name'" in caplog.text


def test_gating_file(tmpdir, caplog):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, "bar.jar"), "w") as fd:
        fd.write("foo")

    img_desc = image_descriptor.copy()
    img_desc["artifacts"] = [{"path": "bar.jar", "dest": "/tmp/destination"}]

    with open(os.path.join(image_dir, "image.yaml"), "w") as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    overrides_descriptor = {
        "schema_version": 1,
        "osbs": {"configuration": {"gating_file": "gating.yaml"}},
    }

    gating = """
--- !Policy
id: kafka-jenkins
product_versions:
  - cvp
decision_context: cvp_default
rules:
  - !PassingTestCaseRule {test_case_name: kafka-jenkins.default.systemtest}
"""
    with open(os.path.join(image_dir, "gating.yaml"), "w") as fd:
        fd.write(gating)

    with open(os.path.join(image_dir, "overrides.yaml"), "w") as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    run_cekit(
        image_dir,
        ["-v", "build", "--dry-run", "--overrides-file", "overrides.yaml", "osbs"],
    )
    gating_path = os.path.join(str(image_dir), "target", "image", "gating.yaml")
    assert os.path.exists(gating_path) is True
    with open(gating_path, "r") as _file:
        f = _file.read()
        assert gating in f


def test_run_descriptor_stdin(tmpdir):
    image_dir = str(tmpdir.mkdir("source"))
    copy_repos(image_dir)

    overrides_descriptor = {"schema_version": 1, "run": {"user": "4321"}}

    with open(os.path.join(image_dir, "overrides.yaml"), "w") as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    run_cekit(
        image_dir,
        [
            "-v",
            "--descriptor",
            "-",
            "build",
            "--dry-run",
            "--overrides-file",
            "overrides.yaml",
            "podman",
        ],
        input=str(image_descriptor),
    )

    assert check_dockerfile(image_dir, "USER 4321", "Containerfile")


@pytest.mark.parametrize(
    "value", ["EAP7.3.0-kie", "python3", "osbs", "16.0-openjdk11-kie"]
)
def test_parse_version(caplog, value):
    caplog.set_level(logging.DEBUG, logger="cekit")

    base.internal_parse_version(value, "foo")

    assert f"version '{value}' does not follow PEP 440" in caplog.text


def run_cekit(cwd, parameters=None, message=None, env=None, input=None):
    if parameters is None:
        parameters = ["build", "--dry-run", "--container-file", "Dockerfile", "podman"]

    if env is None:
        env = {}

    with Chdir(cwd):
        result = CliRunner(env=env).invoke(
            cli, parameters, catch_exceptions=False, input=input
        )
        sys.stdout.write("\n")
        sys.stdout.write(result.output)

        assert result.exit_code == 0

        if message:
            assert message in result.output

        return result


def run_cekit_exception(
    cwd,
    parameters=["-v", "build", "--dry-run", "podman"],
    exit_code=1,
    exception=SystemExit,
    message=None,
):
    with Chdir(cwd):
        result = CliRunner().invoke(cli, parameters, catch_exceptions=False)
        sys.stdout.write("\n")
        sys.stdout.write(result.output)

        assert isinstance(result.exception, exception)
        assert result.exit_code == exit_code

        if message:
            assert message in result.output
