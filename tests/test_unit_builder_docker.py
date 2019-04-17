# -*- encoding: utf-8 -*-

# pylint: disable=protected-access

import logging
import os

from contextlib import contextmanager

import pytest

from cekit.config import Config
from cekit.errors import CekitError
from cekit.builders.docker_builder import DockerBuilder
from cekit.tools import Map

config = Config()


@pytest.fixture(autouse=True)
def reset_config():
    config.cfg['common'] = {}


config = Config()
config.cfg['common'] = {'redhat': True}

docker_success_output = [
    b'{"stream":"Step 1/18 : FROM rhel7:7.5-released\\n"}\r\n',
    b'{"stream":" ---\\u003e 7b875638cfd8\\n"}\r\n',
    b'{"stream":"Step 2/18 : USER root\\n"}\r\n',
    b'{"stream":" ---\\u003e Using cache\\n"}\r\n',
    b'{"stream":" ---\\u003e eeeb32196208\\n"}\r\n',
    b'{"stream":"Step 3/18 : COPY repos/content_sets_odcs.repo /etc/yum.repos.d/\\n"}\r\n',
    b'{"stream":" ---\\u003e Using cache\\n"}\r\n',
    b'{"stream":" ---\\u003e 5b8c17742206\\n"}\r\n',
    b'{"stream":"Step 4/18 : RUN yum makecache\\n"}\r\n',
    b'{"stream":" ---\\u003e Running in bbefb458e837\\n"}\r\n',
    b'{"stream":"Loaded plugins: ovl, product-id, search-disabled-repos, subscription-manager\\n"}\r\n',
    b'{"stream":"This system is not receiving updates. You can use subscription-manager on the host to register and assign subscriptions.\\n"}\r\n',
    b'{"stream":"Metadata Cache Created\\n"}\r\n',
    b'{"stream":" ---\\u003e 3c496e216ae4\\n"}\r\n',
    b'{"stream":"Removing intermediate container bbefb458e837\\n"}\r\n',
    b'{"stream":"Step 5/18 : COPY modules /tmp/scripts/\\n"}\r\n',
    b'{"stream":" ---\\u003e d4128252660d\\n"}\r\n',
    b'{"stream":"Removing intermediate container 14c16d02235a\\n"}\r\n',
    b'{"stream":" ---\\u003e 382fd3d3b632\\n"}\r\n',
    b'{"stream":"Removing intermediate container 7ce407d3f891\\n"}\r\n',
    b'{"stream":"Step 16/18 : RUN rm /etc/yum.repos.d/content_sets_odcs.repo\\n"}\r\n',
    b'{"stream":" ---\\u003e Running in e992e5580f21\\n"}\r\n',
    b'{"stream":" ---\\u003e abf0d7a8ac3e\\n"}\r\n',
    b'{"stream":"Removing intermediate container e992e5580f21\\n"}\r\n',
    b'{"stream":"Step 17/18 : USER 185\\n"}\r\n',
    b'{"stream":" ---\\u003e Running in 1148850ae2df\\n"}\r\n',
    b'{"stream":" ---\\u003e 1a99d0e4c3cc\\n"}\r\n',
    b'{"stream":"Removing intermediate container 1148850ae2df\\n"}\r\n',
    b'{"stream":"Step 18/18 : WORKDIR /home/jboss\\n"}\r\n',
    b'{"stream":" ---\\u003e 985573b8bb7b\\n"}\r\n',
    b'{"stream":"Removing intermediate container 413ed29c9497\\n"}\r\n',
    b'{"stream":"Successfully built 985573b8bb7b\\n"}\r\n'
]

docker_fail_output = [
    b'{"stream":"Step 1/159 : FROM ubi8-dev-preview/ubi-minimal\\n"}\r\n',
    b'{"stream":" ---\\u003e c6070fd793df\\n"}\r\n',
    b'{"stream":"Step 2/159 : USER root\\n"}\r\n',
    b'{"stream":" ---\\u003e Using cache\\n"}\r\n',
    b'{"stream":" ---\\u003e 3841bbce3fdd\\n"}\r\n',
    b'{"stream":"Step 3/159 : COPY modules /tmp/scripts/\\n"}\r\n',
    b'{"stream":" ---\\u003e Using cache\\n"}\r\n',
    b'{"stream":" ---\\u003e 8f6d31270e03\\n"}\r\n',
    b'{"stream":"Step 4/159 : COPY jboss-eap-7.2.1-patch.zip jboss-eap-7.2.zip jolokia-jvm-1.5.0.redhat-1-agent.jar txn-recovery-marker-jdbc-common-1.1.2.Final-redhat-00001.jar txn-recovery-marker-jdbc-hibernate5-1.1.2.Final-redhat-00001.jar openshift-ping-common-1.2.3.Final-redhat-1.jar openshift-ping-dns-1.2.3.Final-redhat-1.jar openshift-ping-kube-1.2.3.Final-redhat-1.jar oauth-20100527.jar activemq-rar-5.11.0.redhat-630371.rar jboss-logmanager-2.1.7.Final.jar rh-sso-7.2.2-eap7-adapter.zip rh-sso-7.2.2-saml-eap7-adapter.zip jmx_prometheus_javaagent-0.3.1.redhat-00006.jar /tmp/artifacts/\\n"}\r\n',
    b'{"stream":" ---\\u003e Using cache\\n"}\r\n',
    b'{"stream":" ---\\u003e b901f2266584\\n"}\r\n',
    b'{"stream":"Step 5/159 : USER root\\n"}\r\n',
    b'{"stream":" ---\\u003e Using cache\\n"}\r\n',
    b'{"stream":" ---\\u003e 81a88b63f47f\\n"}\r\n',
    b'{"stream":"Step 6/159 : RUN microdnf --setopt=tsflags=nodocs install -y maven     \\u0026\\u0026 rpm -q maven\\n"}\r\n',
    b'{"stream":" ---\\u003e Running in 4763fe199ffd\\n"}\r\n',
    b'{"stream":"\\u001b[91m\\n(process:8): librhsm-WARNING **: 09:58:25.023: Found 0 entitlement certificates\\n\\u001b[0m"}\r\n',
    b'{"stream":"\\u001b[91m\\n(process:8): librhsm-WARNING **: 09:58:25.024: Found 0 entitlement certificates\\n\\u001b[0m"}\r\n',
    b'{"stream":"Downloading metadata...\\n"}\r\n',
    b'{"stream":"Downloading metadata...\\n"}\r\n',
    b'{"stream":"\\u001b[91merror: No package matches \'maven\'\\n\\u001b[0m"}\r\n',
    b'{"errorDetail":{"code":1,"message":"The command \'/bin/sh -c microdnf --setopt=tsflags=nodocs install -y maven     \\u0026\\u0026 rpm -q maven\' returned a non-zero code: 1"},"error":"The command \'/bin/sh -c microdnf --setopt=tsflags=nodocs install -y maven     \\u0026\\u0026 rpm -q maven\' returned a non-zero code: 1"}\r\n'
]


def test_docker_client_build(mocker, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

    builder = DockerBuilder(Map({'target': 'something'}), Map({'tags': ['foo', 'bar']}))

    docker_client_class = mocker.patch('cekit.builders.docker_builder.APIClientClass')
    squash_class = mocker.patch('cekit.builders.docker_builder.Squash')
    squash = squash_class.return_value
    docker_client = docker_client_class.return_value
    docker_client_build = mocker.patch.object(
        docker_client, 'build', return_value=docker_success_output)

    builder.generator = Map({'image': {'from': 'FROM'}})

    builder.run()

    squash_class.assert_called_once_with(
        cleanup=True, docker=docker_client, from_layer="FROM", image="985573b8bb7b", log=logging.getLogger('cekit'))
    squash.run.assert_called_once_with()
    docker_client_build.assert_called_once_with(path='something/image', pull=None, rm=True)
    assert "Docker: This system is not receiving updates. You can use subscription-manager on the host to register and assign subscriptions." in caplog.text
    assert "Image built and available under following tags: foo, bar" in caplog.text


def test_docker_client_build_with_failure(mocker, caplog):
    caplog.set_level(logging.DEBUG, logger="cekit")

    builder = DockerBuilder(Map({'target': 'something'}), Map({'tags': ['foo', 'bar']}))

    docker_client_class = mocker.patch('cekit.builders.docker_builder.APIClientClass')
    squash_class = mocker.patch('cekit.builders.docker_builder.Squash')
    squash = squash_class.return_value
    docker_client = docker_client_class.return_value
    docker_client_build = mocker.patch.object(
        docker_client, 'build', return_value=docker_fail_output)

    builder.generator = Map({'image': {'from': 'FROM'}})

    with pytest.raises(CekitError) as exception:
        builder.run()

    assert "Image build failed, see logs above." in str(exception.value)

    squash_class.assert_not_called()
    squash.run.assert_not_called()
    docker_client_build.assert_called_once_with(path='something/image', pull=None, rm=True)
    assert "Docker: Step 3/159 : COPY modules /tmp/scripts/" in caplog.text
    assert "You can look inside the failed image by running 'docker run --rm -ti 81a88b63f47f bash'" in caplog.text
