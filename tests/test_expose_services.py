# test the generation of io.openshift.expose-services label
# -*- encoding: utf-8 -*-

import os
import pytest
import re
import shutil
import socket
import sys
import yaml

from cekit.tools import Chdir
from cekit.cli import Cekit

image_descriptor = {
    'schema_version': 1,
    'from': 'centos:latest',
    'name': 'test/image',
    'version': '1.0',
    'labels': [{'name': 'foo', 'value': 'bar'}, {'name': 'labela', 'value': 'a'}],
    'envs': [{'name': 'baz', 'value': 'qux'}, {'name': 'enva', 'value': 'a'}],
    'run': {'cmd': ['sleep', '60']},
}

@pytest.fixture(scope="module")
def workdir(tmpdir_factory):
    tdir = str(tmpdir_factory.mktemp("image"))
    with open(os.path.join(tdir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)
    return tdir

def getservbyport_works(number, protocol):
    """an always-works alternative for socket.getservbyport"""
    return "MyHTTP"

def getservbyport_doesnt(number, protocol):
    """an always-fails alternative for socket.getservbyport"""
    if (sys.version_info <= (3, 0)):
        raise socket.error("port/proto not found")
    raise OSError("port/proto not found")

def run_cekit_return_dockerfile(mocker, workdir, argv, getservbyport=getservbyport_works):
    # Do not try to validate dependencies while running tests, these are not neccessary
    mocker.patch('cekit.generator.docker.DockerGenerator.dependencies').return_value({})
    """utility function to invoke cekit and return the generated Dockerfile"""
    mocker.patch.object(sys, 'argv', argv)
    mocker.patch.object(socket, 'getservbyport', getservbyport)
    with Chdir(str(workdir)):
        if os.path.exists('target'):
            shutil.rmtree('target')
        try:
            Cekit().parse().run()
        except SystemExit:
            pass
        with open("target/image/Dockerfile", "r") as fd:
            return fd.read()

def test_expose_services_label_not_generated_wo_redhat(mocker, workdir):
    """Test to ensure that io.openshift.expose-services is not auto-generated
    if the --redhat argument is not supplied."""

    dockerfile = run_cekit_return_dockerfile(mocker, workdir,
        ['cekit', '-v', '--config', '/dev/null',
             '--overrides', '{ports: [{value: 8080}]}', 'generate'])

    assert dockerfile.find("io.openshift.expose-services") < 0

def test_expose_services_label_generated(mocker, workdir):
    """Test to ensure that io.openshift.expose-services is auto-generated
    if the --redhat argument is supplied and ports are defined."""

    dockerfile = run_cekit_return_dockerfile(mocker, workdir,
        ['cekit', '-v', '--config', '/dev/null', '--redhat',
             '--overrides', '{ports: [{value: 8080}]}', 'generate'])

    assert dockerfile.find("io.openshift.expose-services") >= 0

def test_expose_services_label_no_ports_not_generated(mocker, workdir):
    """Test to ensure that io.openshift.expose-services is not auto-generated
    if the --redhat argument is supplied but no ports are defined."""

    dockerfile = run_cekit_return_dockerfile(mocker, workdir,
        ['cekit', '-v', '--config', '/dev/null', '--redhat', 'generate'])

    assert dockerfile.find("io.openshift.expose-services") < 0

def test_expose_services_label_not_generated_without_expose(mocker, workdir):
    """Test to ensure that io.openshift.expose-services label does not
    contain a port definition if that port is marked 'expose: False'."""

    dockerfile = run_cekit_return_dockerfile(mocker, workdir,
        ['cekit', '-v', '--config', '/dev/null', '--redhat',
             '--overrides', '{ports: [{value: 8080, expose: False}]}', 'generate'])

    assert not re.match(r'.*LABEL.*io\.openshift\.expose-services=.*8080',
        dockerfile, re.DOTALL)

def test_expose_services_label_not_overridden(mocker, workdir):
    """Test to ensure that io.openshift.expose-services is not auto-generated
    if the label is already defined."""
    dockerfile = run_cekit_return_dockerfile(mocker, workdir,
        ['cekit', '-v', '--config', '/dev/null', '--redhat', '--overrides',
             '{ports: [{value: 8080}], labels: [{name: io.openshift.expose-services, value: Fnord.}]}',
             'generate'])

    assert re.match(r'.*LABEL.*io\.openshift\.expose-services=.*Fnord\.',
        dockerfile, re.DOTALL)

def test_expose_services_generated_default_protocol_tcp(mocker, workdir):
    """Test to ensure that auto-generated io.openshift.expose-services
    label includes the default protocol suffix of /tcp"""

    dockerfile = run_cekit_return_dockerfile(mocker, workdir,
        ['cekit', '-v', '--config', '/dev/null', '--redhat',
         '--overrides', '{ports: [{value: 8080}]}', 'generate'])

    assert re.match(r'.*LABEL.*io\.openshift\.expose-services=.*8080/tcp',
        dockerfile, re.DOTALL)

def test_expose_services_generated_specify_protocol(mocker, workdir):
    """Test to ensure that auto-generated io.openshift.expose-services
    label includes the specified protocol"""

    dockerfile = run_cekit_return_dockerfile(mocker, workdir,
        ['cekit', '-v', '--config', '/dev/null', '--redhat',
         '--overrides', '{ports: [{value: 8080, protocol: udp}]}', 'generate'])

    assert re.match(r'.*LABEL.*io\.openshift\.expose-services=.*8080/udp',
        dockerfile, re.DOTALL)

def test_expose_services_not_generated_no_service(mocker, workdir):
    """Test to ensure that auto-generated io.openshift.expose-services
    label does not include ports that lack a service definition."""

    dockerfile = run_cekit_return_dockerfile(mocker, workdir,
        ['cekit', '-v', '--config', '/dev/null', '--redhat',
         '--overrides', '{ports: [{value: 8080}]}', 'generate'],
         getservbyport=getservbyport_doesnt)

    assert not re.match(r'.*LABEL.*io\.openshift\.expose-services=.*8080/tcp',
        dockerfile, re.DOTALL)

def test_expose_services_service_included(mocker, workdir):
    """Test to ensure that auto-generated io.openshift.expose-services
    label includes the service name for a port"""

    dockerfile = run_cekit_return_dockerfile(mocker, workdir,
        ['cekit', '-v', '--config', '/dev/null', '--redhat',
         '--overrides', '{ports: [{value: 8080}]}', 'generate'])

    assert re.match(r'.*LABEL.*io\.openshift\.expose-services=.*8080/tcp:MyHTTP',
        dockerfile, re.DOTALL)
