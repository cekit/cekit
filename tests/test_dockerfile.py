import os
import re
import sys

import pytest
import yaml
from click.testing import CliRunner

from cekit.cli import cli
from cekit.config import Config
from cekit.descriptor import Repository
from cekit.tools import Chdir
from cekit.version import __version__ as cekit_version

basic_config = {"release": 1, "version": 1, "from": "fromimage", "name": "testimage"}

config = Config()
config.cfg["common"] = {"redhat": True}


def print_test_name(value):
    if str(value).startswith("test"):
        return value
    return "\b"


@pytest.mark.parametrize(
    "name, desc_part, exp_regex",
    [
        (
            "test_run_user",
            {"run": {"user": 1347, "cmd": ["whoami"]}},
            r".*USER 1347\n\s+((#.*)?\n\s+)*CMD.*",
        ),
        (
            "test_default_run_user",
            {"run": {"cmd": ["whatever"]}},
            r'.*USER root\n\s+((#.*)?\n\s+)*CMD \["whatever"\]',
        ),
        (
            "test_custom_cmd",
            {"run": {"cmd": ["/usr/bin/date"]}},
            r'.*CMD \["/usr/bin/date"\]',
        ),
        (
            "test_entrypoint",
            {"run": {"entrypoint": ["/usr/bin/date"]}},
            r'.*ENTRYPOINT \["/usr/bin/date"\]',
        ),
        ("test_workdir", {"run": {"workdir": "/home/jboss"}}, r".*WORKDIR /home/jboss"),
        (
            "test_volumes",
            {
                "volumes": [
                    {"path": "/var/lib"},
                    {"path": "/usr/lib", "name": "path.lib"},
                ]
            },
            r'.*VOLUME \["/var/lib"\]\n\s+VOLUME \["/usr/lib"\]',
        ),
        (
            "test_ports",
            {"ports": [{"value": 8080}, {"expose": False, "value": 9999}]},
            r".*EXPOSE 8080$",
        ),
        (
            "test_env",
            {
                "envs": [
                    {"name": "CONFIG_ENV", "example": 1234},
                    {
                        "name": "COMBINED_ENV",
                        "value": "set_value",
                        "example": "example_value",
                        "description": "This is a description",
                    },
                ]
            },
            r" \\\s+COMBINED_ENV=\"set_value\" \\\s+JBOSS_IMAGE_NAME=\"testimage\" \\\s+JBOSS_IMAGE_VERSION=\"1\"\n",
        ),
        ("test_cekit_label_version", {}, r'.*io.cekit.version="%s".*' % cekit_version),
    ],
    ids=print_test_name,
)
def test_dockerfile_rendering(tmpdir, mocker, name, desc_part, exp_regex):
    mocker.patch("cekit.generator.docker.DockerGenerator.dependencies")
    mocker.patch("cekit.builders.osbs.OSBSBuilder.dependencies")
    target = str(tmpdir.mkdir("target"))
    generate(target, ["--redhat", "build", "--dry-run", "podman"], desc_part)
    assert_dockerfile_contains_regex(target, exp_regex)


def test_dockerfile_docker_odcs_pulp(tmpdir, mocker):
    mocker.patch("odcs.client.odcs.ODCS.new_compose", return_value={"id": 12})
    mocker.patch(
        "odcs.client.odcs.ODCS.wait_for_compose",
        return_value={"state": 2, "result_repofile": "url"},
    )
    mocker.patch.object(Repository, "fetch")
    mocker.patch("cekit.builders.osbs.OSBSBuilder._prepare_dist_git")
    mocker.patch("cekit.generator.docker.DockerGenerator.dependencies")
    target = str(tmpdir.mkdir("target"))
    desc_part = {
        "packages": {"content_sets": {"x86_64": "foo"}, "install": ["a"]},
        "osbs": {"repository": {"name": "repo_name", "branch": "branch_name"}},
    }

    generate(target, ["--redhat", "build", "--dry-run", "podman"], desc_part)
    assert_dockerfile_contains_regex(target, "repos/content_sets_odcs.repo")


def test_dockerfile_docker_odcs_rpm(tmpdir, mocker):
    mocker.patch("odcs.client.odcs.ODCS.new_compose", return_value={"id": 12})
    mocker.patch(
        "odcs.client.odcs.ODCS.wait_for_compose",
        return_value={"state": 2, "result_repofile": "url"},
    )
    mocker.patch.object(Repository, "fetch")
    mocker.patch("cekit.builders.osbs.OSBSBuilder._prepare_dist_git")
    mocker.patch("cekit.builders.osbs.OSBSBuilder._copy_to_dist_git")
    mocker.patch("cekit.builders.osbs.OSBSBuilder._sync_with_dist_git")
    mocker.patch("cekit.builders.osbs.OSBSBuilder.dependencies")

    target = str(tmpdir.mkdir("target"))
    desc_part = {
        "packages": {
            "repositories": [{"name": "foo", "rpm": "foo-repo.rpm"}],
            "install": ["a"],
        },
        "osbs": {"repository": {"name": "repo_name", "branch": "branch_name"}},
    }

    generate(target, ["build", "--dry-run", "osbs"], desc_part)

    assert_dockerfile_contains_regex(target, "RUN yum --setopt=tsflags=nodocs install -y foo-repo.rpm")


def test_dockerfile_docker_odcs_rpm_microdnf(tmpdir, mocker):
    mocker.patch("odcs.client.odcs.ODCS.new_compose", return_value={"id": 12})
    mocker.patch(
        "odcs.client.odcs.ODCS.wait_for_compose",
        return_value={"state": 2, "result_repofile": "url"},
    )
    mocker.patch.object(Repository, "fetch")
    target = str(tmpdir.mkdir("target"))
    desc_part = {
        "packages": {
            "manager": "microdnf",
            "repositories": [{"name": "foo", "rpm": "foo-repo.rpm"}],
            "install": ["a", "b"],
        }
    }

    generate(target, ["build", "--dry-run", "podman"], desc_part)
    assert_dockerfile_contains_regex(
        target,
        "RUN microdnf --setopt=install_weak_deps=0 --setopt=tsflags=nodocs install -y foo-repo.rpm",
    )
    assert_dockerfile_contains_regex(
        target,
        "RUN microdnf --setopt=install_weak_deps=0 --setopt=tsflags=nodocs install -y a b",
    )
    assert_dockerfile_contains_regex(target, "rpm -q a b")


def test_dockerfile_docker_odcs_rpm_microdnf_custom_flag_1(tmpdir, mocker):
    mocker.patch("odcs.client.odcs.ODCS.new_compose", return_value={"id": 12})
    mocker.patch(
        "odcs.client.odcs.ODCS.wait_for_compose",
        return_value={"state": 2, "result_repofile": "url"},
    )
    mocker.patch.object(Repository, "fetch")
    target = str(tmpdir.mkdir("target"))
    desc_part = {
        "packages": {
            "manager": "microdnf",
            "manager_flags": "",
            "repositories": [{"name": "foo", "rpm": "foo-repo.rpm"}],
            "install": ["a", "b"],
        }
    }

    generate(target, ["build", "--dry-run", "podman"], desc_part)
    assert_dockerfile_contains_regex(target, "RUN microdnf  install -y foo-repo.rpm")
    assert_dockerfile_contains_regex(target, "RUN microdnf  install -y a b")
    assert_dockerfile_contains_regex(target, "rpm -q a b")


def test_dockerfile_docker_odcs_rpm_microdnf_custom_flag_2(tmpdir, mocker):
    mocker.patch("odcs.client.odcs.ODCS.new_compose", return_value={"id": 12})
    mocker.patch(
        "odcs.client.odcs.ODCS.wait_for_compose",
        return_value={"state": 2, "result_repofile": "url"},
    )
    mocker.patch.object(Repository, "fetch")
    target = str(tmpdir.mkdir("target"))
    desc_part = {
        "packages": {
            "manager": "microdnf",
            "manager_flags": "--setopt=tsflags=nodocs",
            "repositories": [{"name": "foo", "rpm": "foo-repo.rpm"}],
            "install": ["a", "b"],
        }
    }

    generate(target, ["build", "--dry-run", "podman"], desc_part)
    assert_dockerfile_contains_regex(
        target, "RUN microdnf --setopt=tsflags=nodocs install -y foo-repo.rpm"
    )
    assert_dockerfile_contains_regex(target, "RUN microdnf --setopt=tsflags=nodocs install -y a b")
    assert_dockerfile_contains_regex(target, "rpm -q a b")


def test_dockerfile_osbs_odcs_pulp(tmpdir, mocker):
    mocker.patch("odcs.client.odcs.ODCS.new_compose", return_value={"id": 12})
    mocker.patch(
        "odcs.client.odcs.ODCS.wait_for_compose",
        return_value={"state": 2, "result_repofile": "url"},
    )
    mocker.patch.object(Repository, "fetch")
    mocker.patch("cekit.builders.osbs.OSBSBuilder._prepare_dist_git")
    mocker.patch("cekit.builders.osbs.OSBSBuilder._copy_to_dist_git")
    mocker.patch("cekit.builders.osbs.OSBSBuilder._sync_with_dist_git")
    mocker.patch("cekit.builders.osbs.OSBSBuilder.dependencies")
    config.cfg["common"] = {"redhat": True}

    target = str(tmpdir.mkdir("target"))
    os.makedirs(os.path.join(target, "image"))
    desc_part = {
        "packages": {"content_sets": {"x86_64": "foo"}, "install": ["a"]},
        "osbs": {"repository": {"name": "repo_name", "branch": "branch_name"}},
    }

    generate(target, ["build", "--dry-run", "osbs"], desc_part)

    with open(
        os.path.join(target, "target", "image", "content_sets.yml"), "r"
    ) as _file:
        content_sets = yaml.safe_load(_file)
        assert "x86_64" in content_sets
        assert "foo" in content_sets["x86_64"]
        assert "ppc64le" not in content_sets


def test_dockerfile_osbs_odcs_pulp_no_redhat(tmpdir, mocker):
    mocker.patch("odcs.client.odcs.ODCS.new_compose", return_value={"id": 12})
    mocker.patch(
        "odcs.client.odcs.ODCS.wait_for_compose",
        return_value={"state": 2, "result_repofile": "url"},
    )
    mocker.patch.object(Repository, "fetch")
    mocker.patch("cekit.builders.osbs.OSBSBuilder._prepare_dist_git")
    mocker.patch("cekit.builders.osbs.OSBSBuilder._copy_to_dist_git")
    mocker.patch("cekit.builders.osbs.OSBSBuilder._sync_with_dist_git")
    mocker.patch("cekit.builders.osbs.OSBSBuilder.dependencies")
    config.cfg["common"] = {"redhat": False}

    target = str(tmpdir.mkdir("target"))
    desc_part = {
        "packages": {
            "repositories": [
                {"name": "foo", "odcs": {"pulp": "rhel-7-server-rpms"}},
            ],
            "install": ["a"],
        },
        "osbs": {"repository": {"name": "repo_name", "branch": "branch_name"}},
    }

    generate(target, ["build", "--dry-run", "osbs"], desc_part)

    assert not os.path.exists(os.path.join(target, "image", "content_sets.yml"))


def test_dockerfile_osbs_id_redhat_false(tmpdir, mocker):
    config.cfg["common"]["redhat"] = True
    mocker.patch("odcs.client.odcs.ODCS.new_compose", return_value={"id": 12})
    mocker.patch(
        "odcs.client.odcs.ODCS.wait_for_compose",
        return_value={"state": 2, "result_repofile": "url"},
    )
    mocker.patch.object(Repository, "fetch")
    mocker.patch("cekit.builders.osbs.OSBSBuilder._prepare_dist_git")
    mocker.patch("cekit.builders.osbs.OSBSBuilder._copy_to_dist_git")
    mocker.patch("cekit.builders.osbs.OSBSBuilder._sync_with_dist_git")
    mocker.patch("cekit.builders.osbs.OSBSBuilder.dependencies")
    target = str(tmpdir.mkdir("target"))
    desc_part = {
        "packages": {
            "repositories": [
                {"name": "foo", "id": "foo"},
            ],
            "install": ["a"],
        },
        "osbs": {"repository": {"name": "repo_name", "branch": "branch_name"}},
    }

    generate(target, ["build", "--dry-run", "osbs"], desc_part)

    assert not os.path.exists(os.path.join(target, "image", "content_sets.yml"))


def test_dockerfile_osbs_url_only(tmpdir, mocker):
    mocker.patch("odcs.client.odcs.ODCS.new_compose", return_value={"id": 12})
    mocker.patch(
        "odcs.client.odcs.ODCS.wait_for_compose",
        return_value={"state": 2, "result_repofile": "url"},
    )
    mocker.patch.object(Repository, "fetch")
    mocker.patch("cekit.builders.osbs.OSBSBuilder._prepare_dist_git")
    mocker.patch("cekit.builders.osbs.OSBSBuilder._copy_to_dist_git")
    mocker.patch("cekit.builders.osbs.OSBSBuilder._sync_with_dist_git")
    mocker.patch("cekit.builders.osbs.OSBSBuilder.dependencies")
    target = str(tmpdir.mkdir("target"))
    desc_part = {
        "packages": {
            "repositories": [
                {"name": "foo", "url": {"repository": "foo"}},
            ],
            "install": ["a"],
        },
        "osbs": {"repository": {"name": "repo_name", "branch": "branch_name"}},
    }

    image = generate(target, ["build", "--dry-run", "osbs"], desc_part)

    assert not os.path.exists(os.path.join(target, "image", "content_sets.yml"))
    assert "foo" in [x["url"]["repository"] for x in image["packages"]["set_url"]]


def test_dockerfile_osbs_odcs_rpm(tmpdir, mocker):
    mocker.patch("odcs.client.odcs.ODCS.new_compose", return_value={"id": 12})
    mocker.patch(
        "odcs.client.odcs.ODCS.wait_for_compose",
        return_value={"state": 2, "result_repofile": "url"},
    )
    mocker.patch.object(Repository, "fetch")
    target = str(tmpdir.mkdir("target"))

    generate(
        target,
        ["build", "--dry-run", "podman"],
        descriptor={
            "packages": {
                "repositories": [{"name": "foo", "rpm": "foo-repo.rpm"}],
                "install": ["a"],
            },
            "osbs": {"repository": {"name": "repo_name", "branch": "branch_name"}},
        },
    )

    assert_dockerfile_contains_regex(target, "RUN yum --setopt=tsflags=nodocs install -y foo-repo.rpm")


# https://github.com/cekit/cekit/issues/400
def test_unsupported_package_manager(tmpdir, caplog):
    target = str(tmpdir.mkdir("target"))

    generate(
        target,
        ["-v", "build", "--dry-run", "podman"],
        descriptor={
            "packages": {
                "manager": "something",
                "repositories": [{"name": "foo", "rpm": "foo-repo.rpm"}],
                "install": ["a"],
            },
            "osbs": {"repository": {"name": "repo_name", "branch": "branch_name"}},
        },
        exit_code=1,
    )

    assert "Cannot validate schema: Packages" in caplog.text
    assert "Enum 'something' does not exist. Path: '/manager'" in caplog.text


# https://github.com/cekit/cekit/issues/400
def test_default_package_manager(tmpdir):
    target = str(tmpdir.mkdir("target"))

    generate(
        target,
        ["--nocolor", "-v", "build", "--dry-run", "podman"],
        descriptor={
            "packages": {
                "repositories": [{"name": "foo", "rpm": "foo-repo.rpm"}],
                "install": ["a"],
            },
            "osbs": {"repository": {"name": "repo_name", "branch": "branch_name"}},
        },
    )

    assert_dockerfile_contains_regex(target, "RUN yum --setopt=tsflags=nodocs install -y foo-repo.rpm")
    assert_dockerfile_contains_regex(target, "RUN yum --setopt=tsflags=nodocs install -y a")
    assert_dockerfile_contains_regex(target, "rpm -q a")


# https://github.com/cekit/cekit/issues/400
def test_dockerfile_custom_package_manager_with_overrides(tmpdir):
    target = str(tmpdir.mkdir("target"))

    generate(
        target,
        [
            "-v",
            "build",
            "--overrides",
            '{"packages": {"install": ["b"]}}',
            "--dry-run",
            "podman",
        ],
        descriptor={
            "packages": {
                "manager": "microdnf",
                "repositories": [{"name": "foo", "rpm": "foo-repo.rpm"}],
                "install": ["a"],
            },
            "osbs": {"repository": {"name": "repo_name", "branch": "branch_name"}},
        },
    )
    assert_dockerfile_contains_regex(
        target,
        "RUN microdnf --setopt=install_weak_deps=0 --setopt=tsflags=nodocs install -y foo-repo.rpm",
    )
    assert_dockerfile_contains_regex(
        target,
        "RUN microdnf --setopt=install_weak_deps=0 --setopt=tsflags=nodocs install -y a b",
    )
    assert_dockerfile_contains_regex(target, "rpm -q a")
    assert_dockerfile_contains_regex(target, "RUN microdnf clean all")


# https://github.com/cekit/cekit/issues/462
def test_dockerfile_custom_package_manager_with_overrides_overriden_again(tmpdir):
    target = str(tmpdir.mkdir("target"))

    generate(
        target,
        [
            "-v",
            "build",
            "--overrides",
            '{"packages": {"manager": "dnf", "install": ["b"]}}',
            "--dry-run",
            "podman",
        ],
        descriptor={
            "packages": {
                "manager": "microdnf",
                "repositories": [{"name": "foo", "rpm": "foo-repo.rpm"}],
                "install": ["a"],
            },
            "osbs": {"repository": {"name": "repo_name", "branch": "branch_name"}},
        },
    )
    assert_dockerfile_contains_regex(target, "RUN dnf --setopt=tsflags=nodocs install -y foo-repo.rpm")
    assert_dockerfile_contains_regex(target, "RUN dnf --setopt=tsflags=nodocs install -y a b")
    assert_dockerfile_contains_regex(target, "rpm -q a")
    assert_dockerfile_contains_regex(target, "RUN dnf clean all")


# https://github.com/cekit/cekit/issues/400
def test_dockerfile_osbs_odcs_rpm_microdnf(tmpdir):
    target = str(tmpdir.mkdir("target"))

    generate(
        target,
        ["-v", "build", "--dry-run", "podman"],
        descriptor={
            "packages": {
                "manager": "microdnf",
                "repositories": [{"name": "foo", "rpm": "foo-repo.rpm"}],
                "install": ["a"],
            },
            "osbs": {"repository": {"name": "repo_name", "branch": "branch_name"}},
        },
    )
    assert_dockerfile_contains_regex(
        target,
        "RUN microdnf --setopt=install_weak_deps=0 --setopt=tsflags=nodocs install -y foo-repo.rpm",
    )
    assert_dockerfile_contains_regex(
        target,
        "RUN microdnf --setopt=install_weak_deps=0 --setopt=tsflags=nodocs install -y a",
    )
    assert_dockerfile_contains_regex(target, "rpm -q a")


# https://github.com/cekit/cekit/issues/400
@pytest.mark.parametrize("manager", ["yum", "dnf", "microdnf"])
def test_supported_package_managers(tmpdir, manager):
    target = str(tmpdir.mkdir("target"))

    generate(
        target,
        ["-v", "build", "--dry-run", "podman"],
        descriptor={
            "packages": {
                "manager": manager,
                "repositories": [{"name": "foo", "rpm": "foo-repo.rpm"}],
                "install": ["a"],
            },
            "osbs": {"repository": {"name": "repo_name", "branch": "branch_name"}},
        },
    )
    flags = "--setopt=tsflags=nodocs"
    if "microdnf" in manager:
        flags = "--setopt=install_weak_deps=0 " + flags
    assert_dockerfile_contains_regex(target, "RUN {} {} install -y foo-repo.rpm".format(manager, flags))
    assert_dockerfile_contains_regex(target, "RUN {} {} install -y a".format(manager, flags))
    assert_dockerfile_contains_regex(target, "rpm -q a")


def test_supported_package_managers_apk(tmpdir, caplog):
    target = str(tmpdir.mkdir("target"))

    generate(
        target,
        ["-v", "build", "--dry-run", "podman"],
        descriptor={
            "packages": {
                "manager": "apk",
                "install": ["a"],
                "repositories": [{"name": "foo", "rpm": "foo-repo.rpm"}],
            }
        },
    )
    assert_dockerfile_contains_regex(target, "RUN apk  add a")
    assert_dockerfile_contains_regex(target, "apk info -e a")
    assert (
        "Package manager apk does not support defining repositories, skipping all repositories"
        in caplog.text
    )


def test_supported_package_managers_apt(tmpdir, caplog):
    target = str(tmpdir.mkdir("target"))

    generate(
        target,
        ["-v", "build", "--dry-run", "podman"],
        descriptor={
            "packages": {
                "manager": "apt-get",
                "install": ["a"],
                "repositories": [{"name": "foo", "rpm": "foo-repo.rpm"}],
            }
        },
    )
    assert_dockerfile_contains_regex(
        target, "RUN apt-get update && apt-get --no-install-recommends install -y a"
    )
    assert_dockerfile_contains_regex(target, "dpkg-query --list a")
    assert (
        "Package manager apt-get does not support defining repositories, skipping all repositories"
        in caplog.text
    )


# https://github.com/cekit/cekit/issues/406
def test_dockerfile_do_not_copy_modules_if_no_modules(tmpdir):
    target = str(tmpdir.mkdir("target"))
    generate(target, ["build", "--dry-run", "podman"])
    assert_dockerfile_contains_regex(target, "^((?!COPY modules /tmp/scripts/))")


# https://github.com/cekit/cekit/issues/406
def test_dockerfile_copy_modules_if_modules_defined(tmpdir, caplog):
    target = str(tmpdir.mkdir("target"))
    module_dir = os.path.join(target, "modules", "foo")
    module_yaml_path = os.path.join(module_dir, "module.yaml")

    os.makedirs(module_dir)

    with open(module_yaml_path, "w") as outfile:
        yaml.dump(
            {"name": "foo", "version": "1.0", "execute": [{"script": "configure.sh"}]},
            outfile,
            default_flow_style=False,
        )

    generate(
        target,
        ["-v", "--work-dir", target, "build", "--dry-run", "podman"],
        descriptor={
            "modules": {
                "repositories": [{"name": "modules", "path": "modules"}],
                "install": [{"name": "foo"}],
            }
        },
    )

    assert_dockerfile_contains_regex(target, "COPY modules/foo /tmp/scripts/foo")


def test_dockerfile_destination_of_artifact(mocker, tmpdir):
    mocker.patch("cekit.descriptor.resource.Resource.copy")

    target = str(tmpdir.mkdir("target"))
    generate(
        target,
        ["-v", "build", "--dry-run", "podman"],
        descriptor={
            "artifacts": [
                # URL artifact, default destination
                {"name": "abc", "url": "https://asdasd/one.jar"},
                # URL artifact, custom destination
                {
                    "name": "def",
                    "url": "https://asdasd/two.jar",
                    "dest": "/tmp/custom////",
                },
                # Path artifact, default destination
                {"name": "one", "path": "some/path/one"},
                # Path artifact, custom destination
                {"name": "two", "path": "some/path/two", "dest": "/tmp/custom"},
                # Image artifact, default destination
                {"name": "aaa", "image": "image-name", "path": "/some/path.jar"},
                # Image artifact, custom destination
                {
                    "name": "bbb",
                    "image": "image-name",
                    "path": "/some/other-path.jar",
                    "dest": "/tmp/custom/",
                },
                # Plain artifact, default destination
                {"name": "111", "md5": "md5md5md5"},
                # Plain artifact, custom destination
                {"name": "222", "md5": "md5md5md5", "dest": "/tmp/custom/"},
            ]
        },
    )
    assert_dockerfile_contains_regex(
        target,
        """# Copy 'testimage' image general artifacts to '/tmp/artifacts/' destination""",
    )
    assert_dockerfile_contains_regex(
        target, r"^\s+COPY \\\s+abc \\\s+one \\\s+111 \\\s+/tmp/artifacts/$"
    )
    assert_dockerfile_contains_regex(
        target,
        """# Copy 'testimage' image general artifacts to '/tmp/custom/' destination""",
    )
    assert_dockerfile_contains_regex(target, r"^\s+COPY \\\s+def \\\s+two \\\s+222 \\\s+/tmp/custom/$")
    assert_dockerfile_contains_regex(target, """# Copy 'testimage' image stage artifacts""")
    assert_dockerfile_contains_regex(
        target, r"^\s+COPY --from=image-name /some/path.jar /tmp/artifacts/aaa$"
    )
    assert_dockerfile_contains_regex(
        target, r"^\s+COPY --from=image-name /some/other-path.jar /tmp/custom/bbb$"
    )


# https://github.com/cekit/cekit/issues/648
def test_overrides_applied_to_all_multi_stage_images(tmpdir):
    target = str(tmpdir.mkdir("target"))

    descriptor = [
        {"release": 1, "version": 1, "from": "fromimage", "name": "builderimage"},
        {"release": 1, "version": 1, "from": "fromimage", "name": "targetimage"},
    ]

    generate(
        target,
        [
            "-v",
            "build",
            "--overrides",
            '{"version": "SNAPSHOT"}',
            "--dry-run",
            "podman",
        ],
        descriptor,
    )
    assert_dockerfile_contains_regex(target, "^###### START image 'builderimage:SNAPSHOT'$")
    assert_dockerfile_contains_regex(target, "^###### END image 'builderimage:SNAPSHOT'$")
    assert_dockerfile_contains_regex(target, "^###### START image 'targetimage:SNAPSHOT'$")
    assert_dockerfile_contains_regex(target, "^###### END image 'targetimage:SNAPSHOT'$")


def test_dockerfile_contains_multi_stage_build(tmpdir):
    target = str(tmpdir.mkdir("target"))

    descriptor = [
        {"release": 1, "version": 1, "from": "fromimage", "name": "builderimage"},
        {"release": 1, "version": 1, "from": "fromimage", "name": "targetimage"},
    ]

    generate(
        target,
        [
            "-v",
            "build",
            "--dry-run",
            "docker",
        ],
        descriptor,
    )
    assert_dockerfile_contains_regex(target, "^###### START image 'builderimage:1'$")
    assert_dockerfile_contains_regex(target, "^###### END image 'builderimage:1'$")
    assert_dockerfile_contains_regex(target, "^###### START image 'targetimage:1'$")
    assert_dockerfile_contains_regex(target, "^###### END image 'targetimage:1'$")


def generate(image_dir, command, descriptor=None, exit_code=0):
    desc = basic_config.copy()

    if descriptor:
        if isinstance(descriptor, list):
            desc = descriptor
        else:
            desc.update(descriptor)

    tmp_image_file = os.path.join(image_dir, "image.yaml")

    with open(tmp_image_file, "w") as outfile:
        yaml.dump(desc, outfile, default_flow_style=False)

    with Chdir(image_dir):
        result = CliRunner().invoke(cli, command, catch_exceptions=False)
        sys.stdout.write("\n")
        sys.stdout.write(result.output)

        assert result.exit_code == exit_code

        if exit_code != 0:
            return

        with open(os.path.join(image_dir, "target", "image.yaml"), "r") as desc:
            return yaml.safe_load(desc)


def assert_dockerfile_contains_regex(image_dir, exp_regex):
    with open(os.path.join(image_dir, "target", "image", "Dockerfile"), "r") as fd:
        dockerfile_content = fd.read()
        regex = re.compile(exp_regex, re.MULTILINE)
        assert regex.search(dockerfile_content) is not None
