import glob
import logging
import os
import shutil
import subprocess
import time

import pytest
import yaml

from cekit.descriptor import Image
from cekit.errors import CekitError
from cekit.generator.docker import DockerGenerator
from cekit.tools import Map
from tests.utils import merge_dicts

try:
    from unittest.mock import call
except ImportError:
    from mock import call

from cekit.builders.docker_builder import DockerBuilder
from cekit.config import Config

config = Config()


@pytest.fixture(autouse=True)
def reset_config():
    config.cfg["common"] = {}


def merge_container_yaml(dist_git_dir, src, dest):
    # FIXME - this is temporary needs to be refactored to proper merging
    with open(src, "r") as _file:
        generated = yaml.safe_load(_file)

    target = {}
    if os.path.exists(dest):
        with open(dest, "r") as _file:
            target = yaml.safe_load(_file)

    target.update(generated)
    if glob.glob(os.path.join(dist_git_dir, "repos", "*.repo")):
        if "platforms" in target:
            target["platforms"]["only"] = ["x86_64"]
        else:
            target["platforms"] = {"only": ["x86_64"]}

    with open(dest, "w") as _file:
        yaml.dump(target, _file, default_flow_style=False)


def test_osbs_builder_defaults(mocker):
    mocker.patch.object(subprocess, "run")

    builder = create_builder_object(mocker, "osbs", {})

    assert builder._fedpkg == "fedpkg"
    assert builder._koji == "koji"
    assert builder._koji_url == "https://koji.fedoraproject.org/koji"


def test_osbs_builder_redhat(mocker):
    config.cfg["common"] = {"redhat": True}
    mocker.patch.object(subprocess, "run")

    builder = create_builder_object(mocker, "osbs", {})

    assert builder._fedpkg == "rhpkg"
    assert builder._koji == "brew"
    assert builder._koji_url == "https://brewweb.engineering.redhat.com/brew"


def test_osbs_builder_use_rhpkg_stage(mocker):
    config.cfg["common"] = {"redhat": True}
    mocker.patch.object(subprocess, "run")

    builder = create_builder_object(mocker, "osbs", {"stage": True})

    assert builder._fedpkg == "rhpkg-stage"
    assert builder._koji == "brew-stage"
    assert builder._koji_url == "https://brewweb.stage.engineering.redhat.com/brew"


def test_osbs_builder_custom_commit_msg(mocker):
    mocker.patch.object(subprocess, "run")

    builder = create_builder_object(
        mocker, "osbs", {"stage": True, "commit_message": "foo"}
    )

    assert builder.params.commit_message == "foo"


def test_osbs_builder_nowait(mocker):
    mocker.patch.object(subprocess, "run")

    builder = create_builder_object(mocker, "osbs", {"nowait": True})

    assert builder.params.nowait is True


def test_osbs_builder_user(mocker):
    mocker.patch.object(subprocess, "run")

    builder = create_builder_object(mocker, "osbs", {"user": "UserFoo"})
    assert builder.params.user == "UserFoo"


def test_merge_container_yaml_no_limit_arch(mocker, tmpdir):
    mocker.patch.object(glob, "glob", return_value=False)
    mocker.patch.object(subprocess, "run")

    builder = create_builder_object(mocker, "osbs", {})
    builder.dist_git_dir = str(tmpdir.mkdir("target"))

    container_yaml_f = "container.yaml"

    source = "souce_cont.yaml"
    with open(source, "w") as file_:
        yaml.dump({"tags": ["foo"]}, file_)

    merge_container_yaml(builder.dist_git_dir, source, container_yaml_f)

    with open(container_yaml_f, "r") as file_:
        container_yaml = yaml.safe_load(file_)
    os.remove(container_yaml_f)
    os.remove(source)

    assert "paltforms" not in container_yaml


def test_merge_container_yaml_limit_arch(mocker, tmpdir):
    mocker.patch.object(glob, "glob", return_value=True)
    mocker.patch.object(subprocess, "run")
    builder = create_builder_object(mocker, "osbs", {})
    builder.dist_git_dir = str(tmpdir.mkdir("target"))

    container_yaml_f = "container.yaml"

    source = "souce_cont.yaml"
    with open(source, "w") as file_:
        yaml.dump({"tags": ["foo"]}, file_)

    merge_container_yaml(builder.dist_git_dir, source, container_yaml_f)

    with open(container_yaml_f, "r") as file_:
        container_yaml = yaml.safe_load(file_)
    os.remove(container_yaml_f)
    os.remove(source)

    assert "x86_64" in container_yaml["platforms"]["only"]
    assert len(container_yaml["platforms"]["only"]) == 1


class GitMock(object):
    def add(self, artifacts):
        pass

    def stage_modified(self):
        pass

    @staticmethod
    def repo_info(path):
        pass

    def prepare(self, stage, user=None):
        pass

    def clean(self, artifacts):
        pass


def create_builder_object(
    mocker, builder, params, common_params={"target": "something"}
):
    # TODO: Remove mutable default argument
    if "docker" == builder:
        from cekit.builders.docker_builder import DockerBuilder as BuilderImpl
    elif "osbs" == builder:
        from cekit.builders.osbs import OSBSBuilder as BuilderImpl
    elif "podman" == builder:
        from cekit.builders.podman import PodmanBuilder as BuilderImpl
    elif "buildah" == builder:
        from cekit.builders.buildah import BuildahBuilder as BuilderImpl
    else:
        raise Exception(f"Builder engine {builder} is not supported")

    mocker.patch("cekit.tools.decision")

    builder = BuilderImpl(Map(merge_dicts(common_params, params)))
    builder.dist_git_dir = "/tmp"
    builder.git = GitMock()
    builder.artifacts = []
    return builder


def test_osbs_builder_run_brew_stage(mocker):
    config.cfg["common"] = {"redhat": True}
    params = {"stage": True}

    run = mocker.patch.object(
        subprocess,
        "run",
        autospec=True,
        side_effect=[
            subprocess.CompletedProcess(
                "", 0, "ssh://user:password@something.redhat.com/containers/openjdk"
            ),
            subprocess.CompletedProcess(
                "", 0, "c5a0731b558c8a247dd7f85b5f54462cd5b68b23"
            ),
            subprocess.CompletedProcess("", 0, "12345"),
        ],
    )
    builder = create_builder_object(mocker, "osbs", params)
    builder.generator = Map({"image": Map({})})
    mocker.patch.object(builder, "_wait_for_osbs_task")
    builder.git.branch = "some-branch"
    builder.run()

    run.assert_has_calls(
        [
            call(
                ["git", "config", "--get", "remote.origin.url"],
                stderr=-1,
                stdout=-1,
                check=True,
                universal_newlines=True,
            ),
            call(
                ["git", "rev-parse", "HEAD"],
                stderr=-1,
                stdout=-1,
                check=True,
                universal_newlines=True,
            ),
            call(
                [
                    "brew-stage",
                    "call",
                    "--python",
                    "buildContainer",
                    "--kwargs",
                    "{'src': 'git+https://something.redhat.com/git/containers/openjdk#c5a0731b558c8a247dd7f85b5f54462cd5b68b23', 'target': 'some-branch-containers-candidate', 'opts': {'scratch': True, 'git_branch': 'some-branch', 'yum_repourls': []}}",
                ],
                stderr=-1,
                stdout=-1,
                check=True,
                universal_newlines=True,
            ),
        ]
    )

    builder._wait_for_osbs_task.assert_called_once_with("12345", timeout=7200)


def test_osbs_builder_run_brew(mocker):
    config.cfg["common"] = {"redhat": True}

    run = mocker.patch.object(
        subprocess,
        "run",
        autospec=True,
        side_effect=[
            subprocess.CompletedProcess(
                "", 0, "ssh://user:password@something.redhat.com/containers/openjdk"
            ),
            subprocess.CompletedProcess(
                "", 0, "c5a0731b558c8a247dd7f85b5f54462cd5b68b23"
            ),
            subprocess.CompletedProcess("", 0, "12345"),
        ],
    )
    builder = create_builder_object(mocker, "osbs", {})
    builder.generator = Map({"image": Map({})})
    mocker.patch.object(builder, "_wait_for_osbs_task")
    builder.git.branch = "some-branch"
    builder.run()

    run.assert_has_calls(
        [
            call(
                ["git", "config", "--get", "remote.origin.url"],
                stderr=-1,
                stdout=-1,
                check=True,
                universal_newlines=True,
            ),
            call(
                ["git", "rev-parse", "HEAD"],
                stderr=-1,
                stdout=-1,
                check=True,
                universal_newlines=True,
            ),
            call(
                [
                    "brew",
                    "call",
                    "--python",
                    "buildContainer",
                    "--kwargs",
                    "{'src': 'git+https://something.redhat.com/git/containers/openjdk#c5a0731b558c8a247dd7f85b5f54462cd5b68b23', 'target': 'some-branch-containers-candidate', 'opts': {'scratch': True, 'git_branch': 'some-branch', 'yum_repourls': []}}",
                ],
                stderr=-1,
                stdout=-1,
                check=True,
                universal_newlines=True,
            ),
        ]
    )

    builder._wait_for_osbs_task.assert_called_once_with("12345", timeout=7200)


def test_osbs_builder_run_koji(mocker):
    run = mocker.patch.object(
        subprocess,
        "run",
        autospec=True,
        side_effect=[
            subprocess.CompletedProcess(
                "", 0, "ssh://user:password@something.redhat.com/containers/openjdk"
            ),
            subprocess.CompletedProcess(
                "", 0, "c5a0731b558c8a247dd7f85b5f54462cd5b68b23"
            ),
            subprocess.CompletedProcess("", 0, "12345"),
        ],
    )
    builder = create_builder_object(
        mocker, "osbs", {}, {"redhat": False, "target": "something"}
    )
    builder.generator = Map({"image": Map({})})
    mocker.patch.object(builder, "_wait_for_osbs_task")
    builder.git.branch = "some-branch"
    builder.run()

    run.assert_has_calls(
        [
            call(
                ["git", "config", "--get", "remote.origin.url"],
                stderr=-1,
                stdout=-1,
                check=True,
                universal_newlines=True,
            ),
            call(
                ["git", "rev-parse", "HEAD"],
                stderr=-1,
                stdout=-1,
                check=True,
                universal_newlines=True,
            ),
            call(
                [
                    "koji",
                    "call",
                    "--python",
                    "buildContainer",
                    "--kwargs",
                    "{'src': 'git+https://something.redhat.com/git/containers/openjdk#c5a0731b558c8a247dd7f85b5f54462cd5b68b23', 'target': 'some-branch-containers-candidate', 'opts': {'scratch': True, 'git_branch': 'some-branch', 'yum_repourls': []}}",
                ],
                stderr=-1,
                stdout=-1,
                check=True,
                universal_newlines=True,
            ),
        ]
    )

    builder._wait_for_osbs_task.assert_called_once_with("12345", timeout=7200)


def test_osbs_builder_run_brew_nowait(mocker):
    params = {"nowait": True}

    mocker.patch.object(
        subprocess,
        "run",
        autospec=True,
        side_effect=[
            subprocess.CompletedProcess(
                "", 0, "ssh://user:password@something.redhat.com/containers/openjdk"
            ),
            subprocess.CompletedProcess(
                "", 0, "c5a0731b558c8a247dd7f85b5f54462cd5b68b23"
            ),
            subprocess.CompletedProcess("", 0, "12345"),
        ],
    )
    builder = create_builder_object(mocker, "osbs", params)
    builder.generator = Map({"image": Map({})})
    mocker.patch.object(builder, "_wait_for_osbs_task")
    builder.git.branch = "some-branch"
    builder.run()

    builder._wait_for_osbs_task.assert_not_called()


def test_osbs_builder_run_brew_user(mocker):
    config.cfg["common"] = {"redhat": True}
    params = {"user": "Foo"}

    run = mocker.patch.object(
        subprocess,
        "run",
        autospec=True,
        side_effect=[
            subprocess.CompletedProcess(
                "", 0, "ssh://user:password@something.redhat.com/containers/openjdk"
            ),
            subprocess.CompletedProcess(
                "", 0, "c5a0731b558c8a247dd7f85b5f54462cd5b68b23"
            ),
            subprocess.CompletedProcess("", 0, "12345"),
        ],
    )
    builder = create_builder_object(mocker, "osbs", params)
    builder.generator = Map({"image": Map({})})
    mocker.patch.object(builder, "_wait_for_osbs_task")
    builder.git.branch = "some-branch"
    builder.run()

    run.assert_called_with(
        [
            "brew",
            "--user",
            "Foo",
            "call",
            "--python",
            "buildContainer",
            "--kwargs",
            "{'src': 'git+https://something.redhat.com/git/containers/openjdk#c5a0731b558c8a247dd7f85b5f54462cd5b68b23', 'target': 'some-branch-containers-candidate', 'opts': {'scratch': True, 'git_branch': 'some-branch', 'yum_repourls': []}}",
        ],
        stderr=-1,
        stdout=-1,
        check=True,
        universal_newlines=True,
    )


def test_osbs_builder_run_brew_target_defined_in_descriptor(mocker):
    config.cfg["common"] = {"redhat": True}

    run = mocker.patch.object(
        subprocess,
        "run",
        autospec=True,
        side_effect=[
            subprocess.CompletedProcess(
                "", 0, "ssh://user:password@something.redhat.com/containers/openjdk"
            ),
            subprocess.CompletedProcess(
                "", 0, "c5a0731b558c8a247dd7f85b5f54462cd5b68b23"
            ),
            subprocess.CompletedProcess("", 0, "12345"),
        ],
    )
    builder = create_builder_object(mocker, "osbs", {})
    builder.generator = Map(
        {"image": Map({"osbs": Map({"koji_target": "some-target"})})}
    )
    mocker.patch.object(builder, "_wait_for_osbs_task")
    builder.git.branch = "some-branch"
    builder.run()

    run.assert_called_with(
        [
            "brew",
            "call",
            "--python",
            "buildContainer",
            "--kwargs",
            "{'src': 'git+https://something.redhat.com/git/containers/openjdk#c5a0731b558c8a247dd7f85b5f54462cd5b68b23', 'target': 'some-target', 'opts': {'scratch': True, 'git_branch': 'some-branch', 'yum_repourls': []}}",
        ],
        stderr=-1,
        stdout=-1,
        check=True,
        universal_newlines=True,
    )


def test_osbs_wait_for_osbs_task_finished_successfully(mocker):
    config.cfg["common"] = {"redhat": True}
    builder = create_builder_object(mocker, "osbs", {})

    sleep = mocker.patch.object(time, "sleep")
    run = mocker.patch.object(
        subprocess,
        "run",
        side_effect=[
            subprocess.CompletedProcess(
                "",
                0,
                """{
            "state": 2,
            "create_time": "2019-02-15 13:14:58.278557",
            "create_ts": 1550236498.27856,
            "owner": 2485,
            "host_id": 283,
            "method": "buildContainer",
            "completion_ts": 1550237431.0166,
            "arch": "noarch",
            "id": 20222655
        }""",
            )
        ],
    )

    assert builder._wait_for_osbs_task("12345", timeout=7200) is True

    run.assert_called_with(
        ["brew", "call", "--json-output", "getTaskInfo", "12345"],
        stderr=-1,
        stdout=-1,
        check=True,
        universal_newlines=True,
    )
    sleep.assert_not_called()


def test_osbs_wait_for_osbs_task_in_progress(mocker):
    config.cfg["common"] = {"redhat": True}
    builder = create_builder_object(mocker, "osbs", {})

    sleep = mocker.patch.object(time, "sleep")
    run = mocker.patch.object(
        subprocess,
        "run",
        side_effect=[
            subprocess.CompletedProcess(
                "",
                0,
                """{
            "state": 1,
            "create_time": "2019-02-15 13:14:58.278557",
            "create_ts": 1550236498.27856,
            "owner": 2485,
            "host_id": 283,
            "method": "buildContainer",
            "completion_ts": 1550237431.0166,
            "arch": "noarch",
            "id": 20222655
        }""",
            ),
            subprocess.CompletedProcess(
                "",
                0,
                """{
            "state": 2,
            "create_time": "2019-02-15 13:14:58.278557",
            "create_ts": 1550236498.27856,
            "owner": 2485,
            "host_id": 283,
            "method": "buildContainer",
            "completion_ts": 1550237431.0166,
            "arch": "noarch",
            "id": 20222655
        }""",
            ),
        ],
    )

    assert builder._wait_for_osbs_task("12345", timeout=7200) is True

    run.assert_has_calls(
        [
            call(
                ["brew", "call", "--json-output", "getTaskInfo", "12345"],
                stderr=-1,
                stdout=-1,
                check=True,
                universal_newlines=True,
            ),
            call(
                ["brew", "call", "--json-output", "getTaskInfo", "12345"],
                stderr=-1,
                stdout=-1,
                check=True,
                universal_newlines=True,
            ),
        ]
    )
    sleep.assert_called_once_with(20)


def test_osbs_wait_for_osbs_task_failed(mocker):
    config.cfg["common"] = {"redhat": True}
    builder = create_builder_object(mocker, "osbs", {})

    sleep = mocker.patch.object(time, "sleep")
    run = mocker.patch.object(
        subprocess,
        "run",
        side_effect=[
            subprocess.CompletedProcess(
                "",
                0,
                """{
            "state": 5,
            "create_time": "2019-02-15 13:14:58.278557",
            "create_ts": 1550236498.27856,
            "owner": 2485,
            "host_id": 283,
            "method": "buildContainer",
            "completion_ts": 1550237431.0166,
            "arch": "noarch",
            "id": 20222655
        }""",
            )
        ],
    )

    with pytest.raises(
        CekitError,
        match="Task 12345 did not finish successfully, please check the task logs!",
    ):
        builder._wait_for_osbs_task("12345", timeout=7200)

    run.assert_called_with(
        ["brew", "call", "--json-output", "getTaskInfo", "12345"],
        stderr=-1,
        stdout=-1,
        check=True,
        universal_newlines=True,
    )
    sleep.assert_not_called()


@pytest.mark.parametrize(
    "artifact,src,target",
    [
        (
            {"path": "some-path.jar", "md5": "aaabbb"},
            "image/some-path.jar",
            "osbs/repo/some-path.jar",
        ),
        (
            {"name": "some-name", "path": "some-path.jar", "md5": "aaabbb"},
            "image/some-name",
            "osbs/repo/some-name",
        ),
        (
            {"target": "some-target.jar", "path": "some-path.jar", "md5": "aaabbb"},
            "image/some-target.jar",
            "osbs/repo/some-target.jar",
        ),
        (
            {"name": "some-name", "md5": "aaabbb"},
            "image/some-name",
            "osbs/repo/some-name",
        ),
        (
            {"name": "some-name", "target": "some-target.jar", "md5": "aaabbb"},
            "image/some-target.jar",
            "osbs/repo/some-target.jar",
        ),
    ],
)
def test_osbs_copy_artifacts_to_dist_git(mocker, tmpdir, artifact, src, target):
    os.makedirs(os.path.join(str(tmpdir), "image"))

    mocker.patch("cekit.builders.osbs.OSBSBuilder._sync_with_dist_git")
    mocker.patch("cekit.tools.DependencyHandler.handle")
    mocker.patch("cekit.descriptor.resource.Resource.copy")
    copy_mock = mocker.patch("cekit.builders.osbs.shutil.copy2")

    dist_git_class = mocker.patch("cekit.builders.osbs.Git")
    dist_git_class.return_value = GitMock()

    config.cfg["common"] = {"redhat": True, "work_dir": str(tmpdir)}
    config.cfg["doc"] = {"addhelp": False}

    image_descriptor = {
        "schema_version": 1,
        "from": "centos:7",
        "name": "test/image",
        "version": "1.0",
        "labels": [{"name": "foo", "value": "bar"}, {"name": "labela", "value": "a"}],
        "osbs": {"repository": {"name": "repo", "branch": "branch"}},
        "artifacts": [artifact],
    }

    builder = create_builder_object(
        mocker,
        "osbs",
        {"assume_yes": False},
        {"descriptor": yaml.dump(image_descriptor), "target": str(tmpdir)},
    )

    mocker.patch(
        "cekit.tools.get_brew_url",
        side_effect=subprocess.CalledProcessError(1, "command"),
    )

    builder.prepare()
    builder.before_generate()
    builder.generate()
    builder.before_build()

    dist_git_class.assert_called_once_with(
        os.path.join(str(tmpdir), "osbs", "repo"),
        str(tmpdir),
        "repo",
        "branch",
        "osbs_extra",
        False,
    )

    copy_mock.assert_has_calls(
        [
            mocker.call(
                os.path.join(str(tmpdir), "image", "Dockerfile"),
                os.path.join(str(tmpdir), "osbs/repo/Dockerfile"),
            )
        ]
    )


def test_docker_builder_defaults():
    builder = DockerBuilder(
        Map(merge_dicts({"target": "something"}, {"tags": ["foo", "bar"]}))
    )

    assert builder.params.tags == ["foo", "bar"]


def test_osbs_dist_git_sync_called(mocker, tmpdir):
    mocker.patch("cekit.tools.DependencyHandler.handle")

    image_descriptor = {
        "schema_version": 1,
        "from": "centos:7",
        "name": "test/image",
        "version": "1.0",
        "labels": [{"name": "foo", "value": "bar"}, {"name": "labela", "value": "a"}],
        "osbs": {"repository": {"name": "repo", "branch": "branch"}},
    }

    builder = create_builder_object(
        mocker,
        "osbs",
        {},
        {"descriptor": yaml.dump(image_descriptor), "target": str(tmpdir)},
    )

    prepare_dist_git = mocker.patch.object(builder, "_prepare_dist_git")
    copy_to_dist_git = mocker.patch.object(builder, "_copy_to_dist_git")
    run = mocker.patch.object(builder, "run")

    builder.execute()

    prepare_dist_git.assert_called_once_with()
    copy_to_dist_git.assert_called_once_with()
    run.assert_called_once_with()


def test_osbs_dist_git_sync_NOT_called_when_dry_run_set(mocker, tmpdir):
    mocker.patch("cekit.tools.DependencyHandler.handle")

    image_descriptor = {
        "schema_version": 1,
        "from": "centos:7",
        "name": "test/image",
        "version": "1.0",
        "labels": [{"name": "foo", "value": "bar"}, {"name": "labela", "value": "a"}],
        "osbs": {"repository": {"name": "repo", "branch": "branch"}},
    }

    builder = create_builder_object(
        mocker,
        "osbs",
        {"dry_run": True},
        {"descriptor": yaml.dump(image_descriptor), "target": str(tmpdir)},
    )

    prepare_dist_git = mocker.patch.object(builder, "_prepare_dist_git")
    copy_to_dist_git = mocker.patch.object(builder, "_copy_to_dist_git")
    sync_with_dist_git = mocker.patch.object(builder, "_sync_with_dist_git")
    run = mocker.patch.object(builder, "run")

    builder.execute()

    prepare_dist_git.assert_not_called()
    copy_to_dist_git.assert_not_called()
    sync_with_dist_git.assert_not_called()
    run.assert_not_called()


def test_docker_build_default_tags(mocker):
    builder = DockerBuilder(Map({"target": "something"}))

    docker_client_class = mocker.patch("cekit.builders.docker_builder.docker.APIClient")
    docker_client = docker_client_class.return_value
    mock_generator = mocker.patch.object(builder, "generator")
    mock_generator.get_tags.return_value = ["image/test:1.0", "image/test:latest"]
    mocker.patch.object(builder, "_build_with_docker")
    mocker.patch.object(builder, "_squash", return_value="112321312imageID")

    builder._build_with_docker.return_value = "1654234sdf56"

    builder.run()

    builder._build_with_docker.assert_called_once_with(docker_client)

    tag_calls = [
        mocker.call("112321312imageID", "image/test", tag="1.0"),
        mocker.call("112321312imageID", "image/test", tag="latest"),
    ]
    docker_client.tag.assert_has_calls(tag_calls)


def test_docker_squashing_enabled(mocker):
    builder = DockerBuilder(
        Map(merge_dicts({"target": "something"}, {"tags": ["foo", "bar"]}))
    )

    # None is fine here, default values for params are tested in different place
    assert builder.params.no_squash is None
    assert builder.params.tags == ["foo", "bar"]

    docker_client_class = mocker.patch("cekit.builders.docker_builder.docker.APIClient")
    docker_client = docker_client_class.return_value
    mocker.patch.object(builder, "_build_with_docker")
    mocker.patch.object(builder, "_squash")
    builder._build_with_docker.return_value = "1654234sdf56"

    builder.run()

    builder._build_with_docker.assert_called_once_with(docker_client)
    builder._squash.assert_called_once_with(docker_client, "1654234sdf56")


def test_docker_squashing_disabled(mocker):
    builder = DockerBuilder(
        Map(
            merge_dicts(
                {"target": "something"}, {"no_squash": True, "tags": ["foo", "bar"]}
            )
        )
    )

    assert builder.params.no_squash is True

    docker_client_class = mocker.patch("cekit.builders.docker_builder.docker.APIClient")
    docker_client = docker_client_class.return_value
    mocker.patch.object(builder, "_build_with_docker")
    mocker.patch.object(builder, "_squash")

    builder._build_with_docker.return_value = "1654234sdf56"

    builder.run()

    builder._build_with_docker.assert_called_once_with(docker_client)
    builder._squash.assert_not_called()


def test_docker_squashing_parameters(mocker):
    builder = DockerBuilder(
        Map(merge_dicts({"target": "something"}, {"tags": ["foo", "bar"]}))
    )

    # None is fine here, default values for params are tested in different place
    assert builder.params.no_squash is None

    docker_client_class = mocker.patch("cekit.builders.docker_builder.docker.APIClient")
    squash_class = mocker.patch("cekit.builders.docker_builder.Squash")
    squash = squash_class.return_value
    docker_client = docker_client_class.return_value
    mocker.patch.object(builder, "_build_with_docker", return_value="1654234sdf56")

    builder.generator = Map({"image": {"from": "FROM"}})

    builder.run()

    squash_class.assert_called_once_with(
        cleanup=True,
        docker=docker_client,
        from_layer="FROM",
        image="1654234sdf56",
        log=logging.getLogger("cekit"),
    )
    squash.run.assert_called_once_with()
    builder._build_with_docker.assert_called_once_with(docker_client)


def test_buildah_builder_run(mocker):
    params = {"tags": ["foo", "bar"]}
    run = mocker.patch.object(subprocess, "run")
    builder = create_builder_object(mocker, "buildah", params)
    builder.run()

    run.assert_called_once_with(
        [
            shutil.which("buildah"),
            "build-using-dockerfile",
            "--squash",
            "-t",
            "foo",
            "-t",
            "bar",
            "something/image",
        ],
        stderr=None,
        stdout=None,
        check=True,
        universal_newlines=True,
    )


def test_buildah_builder_run_platform(mocker):
    params = {"tags": ["foo", "bar"], "platform": "linux/amd64,linux/arm64"}
    run = mocker.patch.object(subprocess, "run")
    builder = create_builder_object(mocker, "buildah", params)
    builder.run()

    run.assert_called_once_with(
        [
            shutil.which("buildah"),
            "build-using-dockerfile",
            "--squash",
            "--platform",
            "linux/amd64,linux/arm64",
            "-t",
            "foo",
            "-t",
            "bar",
            "something/image",
        ],
        stderr=None,
        stdout=None,
        check=True,
        universal_newlines=True,
    )


def test_buildah_builder_run_pull(mocker):
    params = {"tags": ["foo", "bar"], "pull": True}
    run = mocker.patch.object(subprocess, "run")
    builder = create_builder_object(mocker, "buildah", params)
    builder.run()

    run.assert_called_once_with(
        [
            shutil.which("buildah"),
            "build-using-dockerfile",
            "--squash",
            "--pull-always",
            "-t",
            "foo",
            "-t",
            "bar",
            "something/image",
        ],
        stderr=None,
        stdout=None,
        check=True,
        universal_newlines=True,
    )


def test_podman_builder_run(mocker):
    params = {"tags": ["foo", "bar"]}
    run = mocker.patch.object(subprocess, "run")
    builder = create_builder_object(mocker, "podman", params)
    builder.run()

    run.assert_called_once_with(
        [
            shutil.which("podman"),
            "build",
            "--squash",
            "-t",
            "foo",
            "-t",
            "bar",
            "something/image",
        ],
        stderr=None,
        stdout=None,
        check=True,
        universal_newlines=True,
    )


def test_podman_builder_run_pull(mocker):
    params = {"tags": ["foo", "bar"], "pull": True}
    run = mocker.patch.object(subprocess, "run")
    builder = create_builder_object(mocker, "podman", params)
    builder.run()

    run.assert_called_once_with(
        [
            shutil.which("podman"),
            "build",
            "--squash",
            "--pull-always",
            "-t",
            "foo",
            "-t",
            "bar",
            "something/image",
        ],
        stderr=None,
        stdout=None,
        check=True,
        universal_newlines=True,
    )


def test_podman_builder_run_platform(mocker):
    params = {
        "tags": ["foo", "bar"],
        "pull": True,
        "platform": "linux/amd64,linux/arm64",
    }
    run = mocker.patch.object(subprocess, "run")
    builder = create_builder_object(mocker, "podman", params)
    builder.run()

    run.assert_called_once_with(
        [
            shutil.which("podman"),
            "build",
            "--squash",
            "--pull-always",
            "--platform",
            "linux/amd64,linux/arm64",
            "-t",
            "foo",
            "-t",
            "bar",
            "something/image",
        ],
        stderr=None,
        stdout=None,
        check=True,
        universal_newlines=True,
    )


def test_podman_builder_run_with_generator(mocker):
    params = Map({"tags": []})
    run = mocker.patch.object(subprocess, "run")
    builder = create_builder_object(mocker, "podman", params)
    builder.generator = DockerGenerator("", "", "", {})
    builder.generator.image = Image(
        yaml.safe_load(
            """
    name: foo
    version: 1.9
    labels:
      - name: test
        value: val1
      - name: label2
        value: val2
    envs:
      - name: env1
        value: env1val
    """
        ),
        "foo",
    )
    builder.run()

    run.assert_called_once_with(
        [
            shutil.which("podman"),
            "build",
            "--squash",
            "-t",
            "foo:1.9",
            "-t",
            "foo:latest",
            "something/image",
        ],
        stderr=None,
        stdout=None,
        check=True,
        universal_newlines=True,
    )


def test_buildah_builder_run_with_generator(mocker):
    params = Map({"tags": []})
    run = mocker.patch.object(subprocess, "run")
    builder = create_builder_object(mocker, "buildah", params)
    builder.generator = DockerGenerator("", "", "", {})
    builder.generator.image = Image(
        yaml.safe_load(
            """
    name: foo
    version: 1.9
    labels:
      - name: test
        value: val1
      - name: label2
        value: val2
    envs:
      - name: env1
        value: env1val
    """
        ),
        "foo",
    )
    builder.run()

    run.assert_called_once_with(
        [
            shutil.which("buildah"),
            "build-using-dockerfile",
            "--squash",
            "-t",
            "foo:1.9",
            "-t",
            "foo:latest",
            "something/image",
        ],
        stderr=None,
        stdout=None,
        check=True,
        universal_newlines=True,
    )


def test_buildah_builder_with_squashing_disabled(mocker):
    params = {"tags": ["foo", "bar"], "no_squash": True}
    run = mocker.patch.object(subprocess, "run")
    builder = create_builder_object(mocker, "buildah", params)
    builder.run()

    run.assert_called_once_with(
        [
            shutil.which("buildah"),
            "build-using-dockerfile",
            "-t",
            "foo",
            "-t",
            "bar",
            "something/image",
        ],
        stderr=None,
        stdout=None,
        check=True,
        universal_newlines=True,
    )


def test_buildah_builder_with_build_arg(mocker):
    params = {"tags": ["foo", "bar"], "no_squash": True, "build_args": ["KEY=VALUE"]}
    run = mocker.patch.object(subprocess, "run")
    builder = create_builder_object(mocker, "buildah", params)
    builder.run()

    run.assert_called_once_with(
        [
            shutil.which("buildah"),
            "build-using-dockerfile",
            "-t",
            "foo",
            "-t",
            "bar",
            "--build-arg=KEY=VALUE",
            "something/image",
        ],
        stderr=None,
        stdout=None,
        check=True,
        universal_newlines=True,
    )


def test_podman_builder_with_squashing_disabled(mocker):
    params = {"no_squash": True}
    run = mocker.patch.object(subprocess, "run")
    builder = create_builder_object(mocker, "podman", params)
    builder.generator = DockerGenerator("", "", "", [])
    builder.generator.image = Image(
        yaml.safe_load(
            """
    name: foo
    version: 1.9
    """
        ),
        "foo",
    )
    builder.run()

    run.assert_called_once_with(
        [
            shutil.which("podman"),
            "build",
            "-t",
            "foo:1.9",
            "-t",
            "foo:latest",
            "something/image",
        ],
        stderr=None,
        stdout=None,
        check=True,
        universal_newlines=True,
    )


def test_podman_builder_with_build_arg(mocker):
    params = {"build_args": ["KEY=VALUE"]}
    run = mocker.patch.object(subprocess, "run")
    builder = create_builder_object(mocker, "podman", params)
    builder.generator = DockerGenerator("", "", "", [])
    builder.generator.image = Image(
        yaml.safe_load(
            """
    name: foo
    version: 1.9
    """
        ),
        "foo",
    )
    builder.run()

    run.assert_called_once_with(
        [
            shutil.which("podman"),
            "build",
            "--squash",
            "-t",
            "foo:1.9",
            "-t",
            "foo:latest",
            "--build-arg=KEY=VALUE",
            "something/image",
        ],
        stderr=None,
        stdout=None,
        check=True,
        universal_newlines=True,
    )


def test_podman_builder_with_build_flag(mocker):
    params = {"build_flag": ["--compress"]}
    run = mocker.patch.object(subprocess, "run")
    builder = create_builder_object(mocker, "podman", params)
    builder.generator = DockerGenerator("", "", "", [])
    builder.generator.image = Image(
        yaml.safe_load(
            """
    name: foo
    version: 1.9
    """
        ),
        "foo",
    )
    builder.run()

    run.assert_called_once_with(
        [
            shutil.which("podman"),
            "build",
            "--squash",
            "-t",
            "foo:1.9",
            "-t",
            "foo:latest",
            "--compress",
            "something/image",
        ],
        stderr=None,
        stdout=None,
        check=True,
        universal_newlines=True,
    )


def test_docker_squashing_disabled_dependencies(mocker, tmpdir, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

    result = (
        "Required CEKit library 'docker-squash' was found as a 'docker_squash' module"
    )
    image_descriptor = {
        "schema_version": 1,
        "from": "centos:7",
        "name": "test/image",
        "version": "1.0",
        "labels": [{"name": "foo", "value": "bar"}, {"name": "labela", "value": "a"}],
    }

    builder = create_builder_object(
        mocker,
        "docker",
        Map({"no_squash": True, "tags": ["foo", "bar"]}),
        Map({"descriptor": yaml.dump(image_descriptor), "target": str(tmpdir)}),
    )
    assert builder.params.no_squash is True
    builder.prepare()
    builder.before_build()
    assert result not in caplog.text

    builder = create_builder_object(
        mocker,
        "docker",
        Map({"tags": ["foo", "bar"]}),
        Map({"descriptor": yaml.dump(image_descriptor), "target": str(tmpdir)}),
    )
    assert builder.params.no_squash is None
    builder.prepare()
    builder.before_build()
    assert result in caplog.text
