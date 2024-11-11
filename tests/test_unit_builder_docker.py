# -*- encoding: utf-8 -*-

import logging
import re

import pytest

from cekit.builders.docker_builder import DockerBuilder
from cekit.errors import CekitError
from cekit.tools import Map
from tests.utils import merge_dicts

docker_success_output = [
    {"stream": "Step 1/18 : FROM rhel7:7.5-released\n"},
    {"stream": " ---> 7b875638cfd8\n"},
    {"stream": "Step 2/18 : USER root\n"},
    {"stream": " ---> Using cache\n"},
    {"stream": " ---> eeeb32196208\n"},
    {"stream": "Step 3/18 : COPY repos/content_sets_odcs.repo /etc/yum.repos.d/\n"},
    {"stream": " ---> Using cache\n"},
    {"stream": " ---> 5b8c17742206\n"},
    {"stream": "Step 4/18 : RUN yum makecache\n"},
    {"stream": " ---> Running in bbefb458e837\n"},
    {
        "stream": "Loaded plugins: ovl, product-id, search-disabled-repos, subscription-manager\n"
    },
    {
        "stream": "This system is not receiving updates. You can use subscription-manager on the host to register and assign subscriptions.\n"
    },
    {"stream": "Metadata Cache Created\n"},
    {"stream": " ---> 3c496e216ae4\n"},
    {"stream": "Removing intermediate container bbefb458e837\n"},
    {"stream": "Step 5/18 : COPY modules /tmp/scripts/\n"},
    {"stream": " ---> d4128252660d\n"},
    {"stream": "Removing intermediate container 14c16d02235a\n"},
    {"stream": " ---> 382fd3d3b632\n"},
    {"stream": "Removing intermediate container 7ce407d3f891\n"},
    {"stream": "Step 16/18 : RUN rm /etc/yum.repos.d/content_sets_odcs.repo\n"},
    {"stream": " ---> Running in e992e5580f21\n"},
    {"stream": " ---> abf0d7a8ac3e\n"},
    {"stream": "Removing intermediate container e992e5580f21\n"},
    {"stream": "Step 17/18 : USER 185\n"},
    {"stream": " ---> Running in 1148850ae2df\n"},
    {"stream": " ---> 1a99d0e4c3cc\n"},
    {"stream": "Removing intermediate container 1148850ae2df\n"},
    {"stream": "Step 18/18 : WORKDIR /home/jboss\n"},
    {"stream": " ---> 985573b8bb7b\n"},
    {"stream": "Removing intermediate container 413ed29c9497\n"},
    {"stream": "Successfully built 985573b8bb7b\n"},
]

docker_fail_output = [
    {"stream": "Step 1/159 : FROM ubi8-dev-preview/ubi-minimal\n"},
    {"stream": " ---> c6070fd793df\n"},
    {"stream": "Step 2/159 : USER root\n"},
    {"stream": " ---> Using cache\n"},
    {"stream": " ---> 3841bbce3fdd\n"},
    {"stream": "Step 3/159 : COPY modules /tmp/scripts/\n"},
    {"stream": " ---> Using cache\n"},
    {"stream": " ---> 8f6d31270e03\n"},
    {
        "stream": "Step 4/159 : COPY jboss-eap-7.2.1-patch.zip jboss-eap-7.2.zip jolokia-jvm-1.5.0.redhat-1-agent.jar txn-recovery-marker-jdbc-common-1.1.2.Final-redhat-00001.jar txn-recovery-marker-jdbc-hibernate5-1.1.2.Final-redhat-00001.jar openshift-ping-common-1.2.3.Final-redhat-1.jar openshift-ping-dns-1.2.3.Final-redhat-1.jar openshift-ping-kube-1.2.3.Final-redhat-1.jar oauth-20100527.jar activemq-rar-5.11.0.redhat-630371.rar jboss-logmanager-2.1.7.Final.jar rh-sso-7.2.2-eap7-adapter.zip rh-sso-7.2.2-saml-eap7-adapter.zip jmx_prometheus_javaagent-0.3.1.redhat-00006.jar /tmp/artifacts/\n"
    },
    {"stream": " ---> Using cache\n"},
    {"stream": " ---> b901f2266584\n"},
    {"stream": "Step 5/159 : USER root\n"},
    {"stream": " ---> Using cache\n"},
    {"stream": " ---> 81a88b63f47f\n"},
    {
        "stream": "Step 6/159 : RUN microdnf --setopt=tsflags=nodocs install -y maven     \u0026\u0026 rpm -q maven\n"
    },
    {"stream": " ---> Running in 4763fe199ffd\n"},
    {
        "stream": "\u001b[91m\n(process:8): librhsm-WARNING **: 09:58:25.023: Found 0 entitlement certificates\n\u001b[0m"
    },
    {
        "stream": "\u001b[91m\n(process:8): librhsm-WARNING **: 09:58:25.024: Found 0 entitlement certificates\n\u001b[0m"
    },
    {"stream": "Downloading metadata...\n"},
    {"stream": "Downloading metadata...\n"},
    {"stream": "\u001b[91merror: No package matches 'maven'\n\u001b[0m"},
    {
        "errorDetail": {
            "code": 1,
            "message": "The command '/bin/sh -c microdnf --setopt=tsflags=nodocs install -y maven     \u0026\u0026 rpm -q maven' returned a non-zero code: 1",
        },
        "error": "The command '/bin/sh -c microdnf --setopt=tsflags=nodocs install -y maven     \u0026\u0026 rpm -q maven' returned a non-zero code: 1",
    },
]


def test_docker_client_build(mocker, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

    squash_class = mocker.patch("cekit.builders.docker_builder.Squash")
    squash = squash_class.return_value
    docker_client_class = mocker.patch("cekit.builders.docker_builder.docker.APIClient")
    docker_client = docker_client_class.return_value
    docker_client_build = mocker.patch.object(
        docker_client, "build", return_value=docker_success_output
    )

    builder = DockerBuilder(
        Map(merge_dicts({"target": "something"}, {"tags": ["foo", "bar"]}))
    )
    builder.generator = Map({"image": {"from": "FROM"}})
    builder.run()

    squash_class.assert_called_once_with(
        cleanup=True,
        docker=docker_client,
        from_layer="FROM",
        image="985573b8bb7b",
        log=logging.getLogger("cekit"),
    )
    squash.run.assert_called_once_with()
    docker_client_build.assert_called_once_with(
        decode=True, path="something/image", pull=None, rm=True
    )
    assert (
        "Docker: This system is not receiving updates. You can use subscription-manager on the host to register and assign subscriptions."
        in caplog.text
    )
    assert "built and available under following tags: foo, bar" in caplog.text


def test_docker_client_build_platform(mocker, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

    mocker.patch("cekit.builders.docker_builder.Squash")
    mocker.patch("cekit.builders.docker_builder.docker.APIClient")
    mocker.patch("subprocess.run")

    builder = DockerBuilder(
        Map(
            merge_dicts(
                {"target": "something"},
                {"tags": ["foo", "bar"]},
                {"platform": "linux/amd64,linux/arm64"},
            )
        )
    )
    builder.generator = Map({"image": {"from": "FROM"}})
    builder.run()

    assert re.match(
        ".*Executing.*docker build.*platform.*linux/amd64,linux/arm64.*",
        caplog.text,
        re.DOTALL,
    )


def test_docker_client_build_with_failure(mocker, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

    builder = DockerBuilder(
        Map(merge_dicts({"target": "something"}, {"tags": ["foo", "bar"]}))
    )

    docker_client_class = mocker.patch("cekit.builders.docker_builder.docker.APIClient")
    squash_class = mocker.patch("cekit.builders.docker_builder.Squash")
    squash = squash_class.return_value
    docker_client = docker_client_class.return_value
    docker_client_build = mocker.patch.object(
        docker_client, "build", return_value=docker_fail_output
    )

    builder.generator = Map({"image": {"from": "FROM"}})

    with pytest.raises(CekitError) as exception:
        builder.run()

    assert "Image build failed, see logs above." in str(exception.value)

    squash_class.assert_not_called()
    squash.run.assert_not_called()
    docker_client_build.assert_called_once_with(
        decode=True, path="something/image", pull=None, rm=True
    )
    assert "Docker: Step 3/159 : COPY modules /tmp/scripts/" in caplog.text
    assert (
        "You can look inside the failed image by running 'docker run --rm -ti 81a88b63f47f bash'"
        in caplog.text
    )


# https://github.com/cekit/cekit/issues/508
def test_docker_tag(mocker):
    builder = DockerBuilder(
        Map(merge_dicts({"target": "something"}, {"tags": ["foo", "bar"]}))
    )

    docker_client_mock = mocker.Mock()

    builder._tag(
        docker_client_mock, "image_id", ["image:latest", "host:5000/repo/image:tag"]
    )

    assert len(docker_client_mock.tag.mock_calls) == 2

    docker_client_mock.tag.assert_has_calls(
        [
            mocker.call("image_id", "image", tag="latest"),
            mocker.call("image_id", "host:5000/repo/image", tag="tag"),
        ]
    )
