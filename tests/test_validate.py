import os
import platform
import shutil
import subprocess
import sys
import pytest
import yaml

from requests.exceptions import ConnectionError  # pylint: disable=redefined-builtin

from cekit.cli import cli
from cekit.descriptor import Repository
from cekit.tools import Chdir
from click.testing import CliRunner

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
    'schema_version': 1,
    'from': 'centos:latest',
    'name': 'test/image',
    'version': '1.0',
    'labels': [{'name': 'foo', 'value': 'bar'}, {'name': 'labela', 'value': 'a'}],
    'run': {'cmd': ['sleep', '60']},
    'modules': {'repositories': [{'name': 'modules',
                                  'path': 'tests/modules/repo_1'}],
                'install': [{'name': 'foo'}]}
}

simple_image_descriptor = {
    'schema_version': 1,
    'from': 'centos:latest',
    'name': 'test/image',
    'version': '1.0'
}

feature_label_test = """
@test
Feature: Test test

  Scenario: Check label foo
    When container is started as uid 0 with process sleep
    then the image should contain label foo with value bar
"""

feature_label_test_overriden = """
@test
Feature: Test test

  Scenario: Check label foo
    When container is started as uid 0 with process sleep
    then the image should contain label foo with value overriden
"""

if sys.version_info.major == 2:
    PermissionError = ConnectionError
    FileNotFoundError = ConnectionError


def run_cekit_cs_overrides(image_dir, mocker, overrides_descriptor):
    mocker.patch.object(subprocess, 'check_output', return_value=odcs_fake_resp)
    mocker.patch.object(Repository, 'fetch')

    copy_repos(image_dir)

    with open(os.path.join(image_dir, 'config'), 'w') as fd:
        fd.write("[common]\n")
        fd.write("redhat = True")

    img_desc = image_descriptor.copy()

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    with open(os.path.join(image_dir, 'overrides.yaml'), 'w') as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    return run_cekit(image_dir, ['-v',
                                 '--config',
                                 'config',
                                 'build',
                                 '--dry-run',
                                 '--overrides-file',
                                 'overrides.yaml',
                                 'docker'])


def test_content_sets_file_container_file(tmpdir, mocker, caplog):
    # Do not try to validate dependencies while running tests, these are not necessary
    mocker.patch('cekit.generator.docker.DockerGenerator.dependencies').return_value({})
    mocker.patch('odcs.client.odcs.ODCS.new_compose', return_value={'id': 12})
    mocker.patch('odcs.client.odcs.ODCS.wait_for_compose', return_value={
                 'state': 2, 'result_repofile': 'url'})
    overrides_descriptor = {
        'schema_version': 1,
        'packages': {'content_sets_file': 'content_sets.yml'},
        'osbs': {'configuration': {'container_file': 'container.yaml'}}}

    content_sets = {'x86_64': ['aaa', 'bbb']}
    container = {'compose': {'pulp_repos': True}}

    image_dir = str(tmpdir.mkdir('source'))

    with open(os.path.join(image_dir, 'content_sets.yml'), 'w') as fd:
        yaml.dump(content_sets, fd, default_flow_style=False)

    with open(os.path.join(image_dir, 'container.yaml'), 'w') as fd:
        yaml.dump(container, fd, default_flow_style=False)

    run_cekit_cs_overrides(image_dir, mocker, overrides_descriptor)

    assert "Requesting ODCS pulp compose for 'aaa bbb' repositories with '[]' flags..." in caplog.text
    assert "Waiting for compose 12 to finish..." in caplog.text
    assert "Compose finished successfully" in caplog.text
    assert "The image has ContentSets repositories specified, all other repositories are removed!" in caplog.text


def test_content_sets_file_container_embedded(tmpdir, mocker, caplog):
    # Do not try to validate dependencies while running tests, these are not necessary
    mocker.patch('cekit.generator.docker.DockerGenerator.dependencies').return_value({})
    mocker.patch('odcs.client.odcs.ODCS.new_compose', return_value={'id': 12})
    mocker.patch('odcs.client.odcs.ODCS.wait_for_compose', return_value={
                 'state': 2, 'result_repofile': 'url'})
    overrides_descriptor = {
        'schema_version': 1,
        'packages': {'content_sets_file': 'content_sets.yml'},
        'osbs': {'configuration': {'container': {'compose': {'pulp_repos': True}}}}}

    content_sets = {'x86_64': ['aaa', 'bbb']}

    image_dir = str(tmpdir.mkdir('source'))

    with open(os.path.join(image_dir, 'content_sets.yml'), 'w') as fd:
        yaml.dump(content_sets, fd, default_flow_style=False)

    run_cekit_cs_overrides(image_dir, mocker, overrides_descriptor)

    assert "Requesting ODCS pulp compose for 'aaa bbb' repositories with '[]' flags..." in caplog.text
    assert "Waiting for compose 12 to finish..." in caplog.text
    assert "Compose finished successfully" in caplog.text
    assert "The image has ContentSets repositories specified, all other repositories are removed!" in caplog.text


def test_content_sets_embedded_container_embedded(tmpdir, mocker, caplog):
    # Do not try to validate dependencies while running tests, these are not necessary
    mocker.patch('cekit.generator.docker.DockerGenerator.dependencies').return_value({})
    mocker.patch('odcs.client.odcs.ODCS.new_compose', return_value={'id': 12})
    mocker.patch('odcs.client.odcs.ODCS.wait_for_compose', return_value={
                 'state': 2, 'result_repofile': 'url'})
    overrides_descriptor = {
        'schema_version': 1,
        'packages': {'content_sets': {'x86_64': ['aaa', 'bbb']}},
        'osbs': {'configuration': {'container': {'compose': {'pulp_repos': True}}}}}

    image_dir = str(tmpdir.mkdir('source'))

    run_cekit_cs_overrides(image_dir, mocker, overrides_descriptor)

    assert "Requesting ODCS pulp compose for 'aaa bbb' repositories with '[]' flags..." in caplog.text
    assert "Waiting for compose 12 to finish..." in caplog.text
    assert "Compose finished successfully" in caplog.text
    assert "The image has ContentSets repositories specified, all other repositories are removed!" in caplog.text


def test_content_sets_embedded_container_file(tmpdir, mocker, caplog):
    # Do not try to validate dependencies while running tests, these are not necessary
    mocker.patch('cekit.generator.docker.DockerGenerator.dependencies').return_value({})
    mocker.patch('odcs.client.odcs.ODCS.new_compose', return_value={'id': 12})
    mocker.patch('odcs.client.odcs.ODCS.wait_for_compose', return_value={
                 'state': 2, 'result_repofile': 'url'})

    overrides_descriptor = {
        'schema_version': 1,
        'packages': {'content_sets': {'x86_64': ['aaa', 'bbb']}},
        'osbs': {'configuration': {'container_file': 'container.yaml'}}}

    image_dir = str(tmpdir.mkdir('source'))
    container = {'compose': {'pulp_repos': True}}

    with open(os.path.join(image_dir, 'container.yaml'), 'w') as fd:
        yaml.dump(container, fd, default_flow_style=False)

    run_cekit_cs_overrides(image_dir, mocker, overrides_descriptor)

    assert "Requesting ODCS pulp compose for 'aaa bbb' repositories with '[]' flags..." in caplog.text
    assert "Waiting for compose 12 to finish..." in caplog.text
    assert "Compose finished successfully" in caplog.text
    assert "The image has ContentSets repositories specified, all other repositories are removed!" in caplog.text


def copy_repos(dst):
    shutil.copytree(os.path.join(os.path.dirname(__file__),
                                 'modules'),
                    os.path.join(dst, 'tests', 'modules'))


@pytest.mark.skipif(platform.system() == 'Darwin', reason="Disabled on macOS, cannot run Docker")
def test_simple_image_build(tmpdir):
    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    run_cekit(image_dir, ['-v', 'build', 'docker'])


@pytest.mark.skipif(platform.system() == 'Darwin', reason="Disabled on macOS, cannot run Docker")
def test_simple_image_test(tmpdir):
    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    feature_files = os.path.join(image_dir, 'tests', 'features', 'test.feature')

    os.makedirs(os.path.dirname(feature_files))

    with open(feature_files, 'w') as fd:
        fd.write(feature_label_test)

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    run_cekit(image_dir, ['-v', 'test', '--image', 'test/image:1.0', 'behave'])

    assert not os.path.exists(os.path.join(image_dir, 'target', 'image', 'Dockerfile'))


def test_image_generate_with_multiple_overrides(tmpdir):
    override1 = "{'labels': [{'name': 'foo', 'value': 'bar'}]}"

    override2 = "{'labels': [{'name': 'foo', 'value': 'baz'}]}"

    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    overrides_descriptor = {
        'schema_version': 1,
        'modules': {'repositories': [{'name': 'modules',
                                      'path': 'tests/modules/repo_2'}]}}

    with open(os.path.join(image_dir, 'overrides.yaml'), 'w') as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    run_cekit(image_dir, ['-v',
                          'build',
                          '--overrides',
                          override1,
                          '--overrides',
                          override2,
                          '--dry-run',
                          'docker'])

    effective_image = {}
    with open(os.path.join(image_dir, 'target', 'image.yaml'), 'r') as file_:
        effective_image = yaml.safe_load(file_)

    assert {'name': 'foo', 'value': 'baz'} in effective_image['labels']


@pytest.mark.skipif(platform.system() == 'Darwin', reason="Disabled on macOS, cannot run Docker")
def test_image_test_with_override(tmpdir):
    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    feature_files = os.path.join(image_dir, 'tests', 'features', 'test.feature')

    os.makedirs(os.path.dirname(feature_files))

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    overrides_descriptor = {'labels': [{'name': 'foo', 'value': 'overriden'}]}

    with open(os.path.join(image_dir, 'overrides.yaml'), 'w') as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    with open(feature_files, 'w') as fd:
        fd.write(feature_label_test_overriden)

    run_cekit(image_dir, ['-v',
                          'build',
                          '--overrides-file',
                          'overrides.yaml',
                          'docker'])

    effective_image = {}
    with open(os.path.join(image_dir, 'target', 'image.yaml'), 'r') as file_:
        effective_image = yaml.safe_load(file_)

    assert {'name': 'foo', 'value': 'overriden'} in effective_image['labels']

    run_cekit(image_dir, ['-v', 'test', '--image', 'test/image:1.0', 'behave'])


@pytest.mark.skipif(platform.system() == 'Darwin', reason="Disabled on macOS, cannot run Docker")
def test_image_test_with_multiple_overrides(tmpdir):
    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    feature_files = os.path.join(image_dir, 'tests', 'features', 'test.feature')

    os.makedirs(os.path.dirname(feature_files))

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    overrides_descriptor = {'labels': [{'name': 'foo', 'value': 'X'}]}

    with open(os.path.join(image_dir, 'overrides.yaml'), 'w') as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    overrides_descriptor2 = {'labels': [{'name': 'foo', 'value': 'Y'}]}

    with open(os.path.join(image_dir, 'overrides2.yaml'), 'w') as fd:
        yaml.dump(overrides_descriptor2, fd, default_flow_style=False)

    with open(feature_files, 'w') as fd:
        fd.write(feature_label_test_overriden)

    run_cekit(image_dir, ['-v',
                          'build',
                          '--overrides-file',
                          'overrides.yaml',
                          '--overrides-file',
                          'overrides2.yaml',
                          '--overrides',
                          "{'labels': [{'name': 'foo', 'value': 'overriden'}]}",
                          'docker'])

    effective_image = {}
    with open(os.path.join(image_dir, 'target', 'image.yaml'), 'r') as file_:
        effective_image = yaml.safe_load(file_)

    assert {'name': 'foo', 'value': 'overriden'} in effective_image['labels']

    run_cekit(image_dir, ['-v', 'test', '--image', 'test/image:1.0', 'behave'])


@pytest.mark.skipif(platform.system() == 'Darwin', reason="Disabled on macOS, cannot run Docker")
def test_image_test_with_override_on_cmd(tmpdir):
    overrides_descriptor = "{'labels': [{'name': 'foo', 'value': 'overriden'}]}"

    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    feature_files = os.path.join(image_dir, 'tests', 'features', 'test.feature')

    os.makedirs(os.path.dirname(feature_files))

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    with open(feature_files, 'w') as fd:
        fd.write(feature_label_test_overriden)

    run_cekit(image_dir,
              ['-v',
               'build',
               '--overrides', overrides_descriptor,
               'docker'])

    run_cekit(image_dir, ['-v', 'test', '--image', 'test/image:1.0', 'behave'])


def test_module_override(tmpdir):
    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    overrides_descriptor = {
        'schema_version': 1,
        'modules': {'repositories': [{'name': 'modules',
                                      'path': 'tests/modules/repo_2'}]}}

    with open(os.path.join(image_dir, 'overrides.yaml'), 'w') as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    run_cekit(image_dir,
              ['-v',
               'build',
               '--dry-run',
               '--overrides-file', 'overrides.yaml',
               'docker'])

    module_dir = os.path.join(image_dir,
                              'target',
                              'image',
                              'modules',
                              'foo')

    assert os.path.exists(os.path.join(module_dir,
                                       'overriden'))

    assert not os.path.exists(os.path.join(module_dir,
                                           'original'))

    assert check_dockerfile(image_dir, 'RUN [ "bash", "-x", "/tmp/scripts/foo/script" ]')


# https://github.com/cekit/cekit/issues/489
def test_override_add_module_and_packages_in_overrides(tmpdir):
    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(simple_image_descriptor, fd, default_flow_style=False)

    overrides_descriptor = {
        'schema_version': 1,
        'modules': {
            'repositories': [
                {
                    'name': 'modules',
                    'path': 'tests/modules/repo_3'
                }
            ]
        }
    }

    with open(os.path.join(image_dir, 'overrides.yaml'), 'w') as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    run_cekit(image_dir,
              ['-v',
               'build',
               '--dry-run',
               '--overrides-file', 'overrides.yaml',
               '--overrides', '{"modules": {"install": [{"name": "master"}, {"name": "child"}] } }',
               '--overrides', '{"packages": {"install": ["package1", "package2"] } }',
               '--overrides', '{"artifacts": [{"name": "test", "path": "image.yaml"}] }',
               'docker'])

    assert check_dockerfile(
        image_dir, 'RUN yum --setopt=tsflags=nodocs install -y package1 package2 \\')
    assert check_dockerfile(image_dir, 'RUN [ "bash", "-x", "/tmp/scripts/master/script_a" ]')
    assert check_dockerfile_text(
        image_dir, '        COPY \\\n            test \\\n            /tmp/artifacts/')


# Test work of workaround for https://bugzilla.redhat.com/show_bug.cgi?id=1700341
def test_microdnf_clean_all_cmd_present(tmpdir):
    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    overrides_descriptor = {
        'schema_version': 1,
        'packages': {'manager': 'microdnf'}
    }

    with open(os.path.join(image_dir, 'overrides.yaml'), 'w') as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    run_cekit(image_dir,
              ['-v',
               'build',
               '--dry-run',
               '--overrides-file', 'overrides.yaml',
               '--overrides', '{"packages": {"install": ["package1", "package2"] } }',
               'docker'])

    required_matches = [
        'RUN microdnf --setopt=tsflags=nodocs install -y package1 package2 \\',
        '&& microdnf clean all \\',
        '&& rpm -q package1 package2'
    ]

    for match in required_matches:
        assert check_dockerfile(image_dir, match)


def check_dockerfile(image_dir, match):
    with open(os.path.join(image_dir, 'target', 'image', 'Dockerfile'), 'r') as fd:
        for line in fd.readlines():
            if line.strip() == match.strip():
                return True
    return False


def check_dockerfile_text(image_dir, match):
    with open(os.path.join(image_dir, 'target', 'image', 'Dockerfile'), 'r') as fd:
        dockerfile = fd.read()
        print("MATCH:\n{}".format(match))
        print("DOCKERFILE:\n{}".format(dockerfile))
        if match in dockerfile:
            return True
    return False


def check_dockerfile_uniq(image_dir, match):
    found = False
    with open(os.path.join(image_dir, 'target', 'image', 'Dockerfile'), 'r') as fd:
        for line in fd.readlines():
            if line.strip() == match.strip():
                if found:
                    return False
                else:
                    found = True
    return found


def test_local_module_not_injected(tmpdir):
    image_dir = str(tmpdir.mkdir('source'))

    local_desc = image_descriptor.copy()
    local_desc.pop('modules')

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(local_desc, fd, default_flow_style=False)

    shutil.copytree(os.path.join(os.path.dirname(__file__),
                                 'modules', 'repo_1'),
                    os.path.join(image_dir, 'modules'))
    run_cekit(image_dir)
    assert not os.path.exists(os.path.join(image_dir,
                                           'target',
                                           'image',
                                           'modules'))


def test_run_override_user(tmpdir):
    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    overrides_descriptor = {
        'schema_version': 1,
        'run': {'user': '4321'}}

    with open(os.path.join(image_dir, 'overrides.yaml'), 'w') as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    run_cekit(image_dir,
              ['-v',
               'build',
               '--dry-run',
               '--overrides-file', 'overrides.yaml',
               'docker'])

    assert check_dockerfile(image_dir, 'USER 4321')


def test_run_override_artifact(tmpdir):
    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, 'bar.jar'), 'w') as fd:
        fd.write('foo')

    img_desc = image_descriptor.copy()
    img_desc['artifacts'] = [{'url': 'https://foo/bar.jar'}]

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    overrides_descriptor = {
        'schema_version': 1,
        'artifacts': [{'path': 'bar.jar'}]}

    with open(os.path.join(image_dir, 'overrides.yaml'), 'w') as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    run_cekit(image_dir,
              ['-v',
               'build',
               '--dry-run',
               '--overrides-file', 'overrides.yaml',
               'docker'])

    assert check_dockerfile_uniq(image_dir, 'bar.jar \\')


def test_run_path_artifact_brew(tmpdir, caplog):
    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, 'bar.jar'), 'w') as fd:
        fd.write('foo')

    img_desc = image_descriptor.copy()
    img_desc['artifacts'] = [{'name': 'aaa',
                              'md5': 'd41d8cd98f00b204e9800998ecf8427e',
                              'target': 'target_foo'}]

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    run_cekit_exception(image_dir)

    assert "Cekit is not able to fetch resource 'aaa' automatically. Please use cekit-cache command to add this artifact manually." in caplog.text


def test_run_path_artifact_target(tmpdir):
    image_dir = str(tmpdir.mkdir('source'))

    copy_repos(image_dir)

    with open(os.path.join(image_dir, 'bar.jar'), 'w') as fd:
        fd.write('foo')

    img_desc = image_descriptor.copy()
    img_desc['artifacts'] = [{'path': 'bar.jar',
                              'target': 'target_foo'}]

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    run_cekit(image_dir)

    assert check_dockerfile_uniq(image_dir, 'target_foo \\')


def test_execution_order(tmpdir):
    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    img_desc = image_descriptor.copy()
    img_desc['modules']['install'] = [{'name': 'master'}]
    img_desc['modules']['repositories'] = [{'name': 'modules',
                                            'path': 'tests/modules/repo_3'}]

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
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
        RUN [ "bash", "-x", "/tmp/scripts/child_of_child/script_d" ]
###### /
###### END module 'child_of_child:1.0'

###### START module 'child2_of_child:1.0'
###### \\
        # Copy 'child2_of_child' module content
        COPY modules/child2_of_child /tmp/scripts/child2_of_child
        # Custom scripts from 'child2_of_child' module
        USER root
        RUN [ "bash", "-x", "/tmp/scripts/child2_of_child/scripti_e" ]
###### /
###### END module 'child2_of_child:1.0'

###### START module 'child3_of_child:1.0'
###### \\
        # Copy 'child3_of_child' module content
        COPY modules/child3_of_child /tmp/scripts/child3_of_child
        # Custom scripts from 'child3_of_child' module
        USER root
        RUN [ "bash", "-x", "/tmp/scripts/child3_of_child/script_f" ]
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
        RUN [ "bash", "-x", "/tmp/scripts/child/script_b" ]
###### /
###### END module 'child:1.0'

###### START module 'child_2:1.0'
###### \\
        # Copy 'child_2' module content
        COPY modules/child_2 /tmp/scripts/child_2
        # Custom scripts from 'child_2' module
        USER root
        RUN [ "bash", "-x", "/tmp/scripts/child_2/script_c" ]
###### /
###### END module 'child_2:1.0'

###### START module 'child_of_child3:1.0'
###### \\
        # Copy 'child_of_child3' module content
        COPY modules/child_of_child3 /tmp/scripts/child_of_child3
        # Custom scripts from 'child_of_child3' module
        USER root
        RUN [ "bash", "-x", "/tmp/scripts/child_of_child3/script_g" ]
###### /
###### END module 'child_of_child3:1.0'

###### START module 'child2_of_child3:1.0'
###### \\
        # Copy 'child2_of_child3' module content
        COPY modules/child2_of_child3 /tmp/scripts/child2_of_child3
        # Custom scripts from 'child2_of_child3' module
        USER root
        RUN [ "bash", "-x", "/tmp/scripts/child2_of_child3/script_h" ]
###### /
###### END module 'child2_of_child3:1.0'

###### START module 'child_3:1.0'
###### \\
        # Copy 'child_3' module content
        COPY modules/child_3 /tmp/scripts/child_3
###### /
###### END module 'child_3:1.0'

###### START module 'master:1.0'
###### \\
        # Copy 'master' module content
        COPY modules/master /tmp/scripts/master
        # Set 'master' module defined environment variables
        ENV \\
            foo="master" 
        # Custom scripts from 'master' module
        USER root
        RUN [ "bash", "-x", "/tmp/scripts/master/script_a" ]
###### /
###### END module 'master:1.0'
"""
    assert check_dockerfile_text(image_dir, expected_modules_order)


def test_override_modules_child(tmpdir, mocker):
    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    img_desc = image_descriptor.copy()
    img_desc['modules']['install'] = [{'name': 'master'}]
    img_desc['modules']['repositories'] = [{'name': 'modules',
                                            'path': 'tests/modules/repo_3'}]

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    run_cekit(image_dir)
    assert check_dockerfile_text(image_dir, 'foo="master"')


def test_override_modules_flat(tmpdir, mocker):
    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    img_desc = image_descriptor.copy()
    img_desc['modules']['install'] = [{'name': 'mod_1'},
                                      {'name': 'mod_2'},
                                      {'name': 'mod_3'},
                                      {'name': 'mod_4'}]
    img_desc['modules']['repositories'] = [{'name': 'modules',
                                            'path': 'tests/modules/repo_4'}]

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    run_cekit(image_dir)

    assert check_dockerfile_text(image_dir, 'foo="mod_2"')
    assert not check_dockerfile_text(image_dir, "RUN yum clean all")


def test_execution_order_flat(tmpdir, mocker):
    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    img_desc = image_descriptor.copy()
    img_desc['modules']['install'] = [{'name': 'mod_1'},
                                      {'name': 'mod_2'},
                                      {'name': 'mod_3'},
                                      {'name': 'mod_4'}]
    img_desc['modules']['repositories'] = [{'name': 'modules',
                                            'path': 'tests/modules/repo_4'}]

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
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
        RUN [ "bash", "-x", "/tmp/scripts/mod_1/a" ]
        USER root
        RUN [ "bash", "-x", "/tmp/scripts/mod_1/b" ]
        USER root
        RUN [ "bash", "-x", "/tmp/scripts/mod_1/c" ]
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
        RUN [ "bash", "-x", "/tmp/scripts/mod_2/a" ]
        USER root
        RUN [ "bash", "-x", "/tmp/scripts/mod_2/b" ]
        USER root
        RUN [ "bash", "-x", "/tmp/scripts/mod_2/c" ]
###### /
###### END module 'mod_2:1.0'

###### START module 'mod_3:1.0'
###### \\
        # Copy 'mod_3' module content
        COPY modules/mod_3 /tmp/scripts/mod_3
        # Custom scripts from 'mod_3' module
        USER root
        RUN [ "bash", "-x", "/tmp/scripts/mod_3/a" ]
        USER root
        RUN [ "bash", "-x", "/tmp/scripts/mod_3/b" ]
        USER root
        RUN [ "bash", "-x", "/tmp/scripts/mod_3/c" ]
###### /
###### END module 'mod_3:1.0'

###### START module 'mod_4:1.0'
###### \\
        # Copy 'mod_4' module content
        COPY modules/mod_4 /tmp/scripts/mod_4
        # Custom scripts from 'mod_4' module
        USER root
        RUN [ "bash", "-x", "/tmp/scripts/mod_4/a" ]
        USER root
        RUN [ "bash", "-x", "/tmp/scripts/mod_4/b" ]
        USER root
        RUN [ "bash", "-x", "/tmp/scripts/mod_4/c" ]
###### /
###### END module 'mod_4:1.0'
"""
    assert check_dockerfile_text(image_dir, expected_modules_order)
    assert not check_dockerfile_text(image_dir, "RUN yum clean all")


def test_package_related_commands_packages_in_module(tmpdir, mocker):
    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    img_desc = image_descriptor.copy()
    img_desc['modules']['install'] = [{'name': 'packages_module'}, {'name': 'packages_module_1'}]
    img_desc['modules']['repositories'] = [{'name': 'modules',
                                            'path': 'tests/modules/repo_packages'}]

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    run_cekit(image_dir)

    expected_packages_order_install = """
###### START module 'packages_module:1.0'
###### \\
        # Copy 'packages_module' module content
        COPY modules/packages_module /tmp/scripts/packages_module
        # Switch to 'root' user to install 'packages_module' module defined packages
        USER root
        # Install packages defined in the 'packages_module' module
        RUN yum --setopt=tsflags=nodocs install -y kernel java \\
            && rpm -q kernel java
###### /
###### END module 'packages_module:1.0'

###### START module 'packages_module_1:1.0'
###### \\
        # Copy 'packages_module_1' module content
        COPY modules/packages_module_1 /tmp/scripts/packages_module_1
        # Switch to 'root' user to install 'packages_module_1' module defined packages
        USER root
        # Install packages defined in the 'packages_module_1' module
        RUN yum --setopt=tsflags=nodocs install -y wget mc \\
            && rpm -q wget mc
###### /
###### END module 'packages_module_1:1.0'
"""

    assert check_dockerfile_text(image_dir, expected_packages_order_install)
    assert check_dockerfile_text(
        image_dir, "RUN yum clean all && [ ! -d /var/cache/yum ] || rm -rf /var/cache/yum")


def test_package_related_commands_packages_in_image(tmpdir, mocker):
    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    img_desc = image_descriptor.copy()
    img_desc['packages'] = {'install': ['wget', 'mc']}

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    run_cekit(image_dir)

    expected_packages_install = """
        # Switch to 'root' user to install 'test/image' image defined packages
        USER root
        # Install packages defined in the 'test/image' image
        RUN yum --setopt=tsflags=nodocs install -y wget mc \\
            && rpm -q wget mc
"""

    assert check_dockerfile_text(image_dir, expected_packages_install)


def test_nonexisting_image_descriptor(mocker, tmpdir, caplog):
    image_dir = str(tmpdir.mkdir('source'))

    run_cekit_exception(image_dir,
                        ['-v',
                         '--descriptor', 'nonexisting.yaml',
                         'build',
                         'docker'])

    assert "Descriptor could not be found on the 'nonexisting.yaml' path, please check your arguments!" in caplog.text


def test_nonexisting_override_file(mocker, tmpdir, caplog):
    image_dir = str(tmpdir.mkdir('source'))
    img_desc = image_descriptor.copy()

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    run_cekit_exception(image_dir,
                        ['-v',
                         'build',
                         '--dry-run',
                         '--overrides-file', 'nonexisting.yaml',
                         'docker'])

    assert "Loading override 'nonexisting.yaml'" in caplog.text
    assert "Descriptor could not be found on the 'nonexisting.yaml' path, please check your arguments!" in caplog.text


def test_incorrect_override_file(mocker, tmpdir, caplog):
    image_dir = str(tmpdir.mkdir('source'))
    img_desc = image_descriptor.copy()

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(img_desc, fd, default_flow_style=False)

    run_cekit_exception(image_dir,
                        ['-v',
                         'build',
                         '--dry-run',
                         '--overrides', '{wrong!}',
                         'docker'])

    assert "Loading override '{wrong!}'" in caplog.text
    assert "Schema validation failed" in caplog.text
    assert "Key 'wrong!' was not defined" in caplog.text


def test_simple_image_build_error_local_docker_socket_permission_denied(tmpdir, mocker, caplog):
    mocker.patch('urllib3.connectionpool.HTTPConnectionPool.urlopen',
                 side_effect=PermissionError())

    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    run_cekit_exception(image_dir, ['-v',
                                    'build',
                                    'docker'])

    assert "Could not connect to the Docker daemon at 'http+docker://localhost', please make sure the Docker daemon is running" in caplog.text


def test_simple_image_build_error_local_docker_stopped(tmpdir, mocker, caplog):
    mocker.patch('urllib3.connectionpool.HTTPConnectionPool.urlopen',
                 side_effect=FileNotFoundError())

    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    run_cekit_exception(image_dir,
                        ['-v',
                         'build',
                         'docker'])

    assert "Could not connect to the Docker daemon at 'http+docker://localhost', please make sure the Docker daemon is running" in caplog.text


def test_simple_image_build_error_connection_error_remote_docker_with_custom_docker_host(tmpdir, mocker, monkeypatch, caplog):
    mocker.patch('urllib3.connectionpool.HTTPConnectionPool.urlopen',
                 side_effect=PermissionError())

    monkeypatch.setenv("DOCKER_HOST", "tcp://127.0.0.1:1234")

    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    run_cekit_exception(image_dir, ['-v',
                                    'build',
                                    'docker'])

    assert "Could not connect to the Docker daemon at 'http://127.0.0.1:1234', please make sure the Docker daemon is running" in caplog.text
    assert "If Docker daemon is running, please make sure that you specified valid parameters in the 'DOCKER_HOST' environment variable, examples: 'unix:///var/run/docker.sock', 'tcp://192.168.22.33:1234'. You may also need to specify 'DOCKER_TLS_VERIFY', and 'DOCKER_CERT_PATH' environment variables" in caplog.text


# https://github.com/cekit/cekit/issues/538
@pytest.mark.skipif(platform.system() == 'Darwin', reason="Disabled on macOS, cannot run Docker")
def test_proper_decoding(tmpdir, caplog):
    image_dir = str(tmpdir.mkdir('source'))

    shutil.copy2(
        os.path.join(os.path.dirname(__file__), 'images', 'image-gh-538-py27-encoding.yaml'),
        os.path.join(image_dir, 'image.yaml')
    )

    run_cekit(image_dir,
              ['-v',
               'build',
               'docker'])

    assert "Finished!" in caplog.text


# https://github.com/cekit/cekit/issues/533
@pytest.mark.parametrize('parameter', ['content_sets', 'content_sets_file'])
def test_disabling_content_sets(tmpdir, caplog, parameter):
    image_dir = str(tmpdir.mkdir('source'))

    shutil.copy2(
        os.path.join(os.path.dirname(__file__), 'images',
                     'image-gh-533-disable-content-sets-file.yaml'),
        os.path.join(image_dir, 'image.yaml')
    )

    with open(os.path.join(image_dir, 'content_sets.yml'), 'w') as fd:
        yaml.dump({'x86_64': ['rhel-server-rhscl-7-rpms', 'rhel-7-server-rpms']},
                  fd, default_flow_style=False)

    run_cekit(image_dir,
              ['-v',
               'build',
               '--dry-run',
               # Ugly, but double braces are required for 'format to work'
               '--overrides', '{{"packages": {{"{0}": ~}}}}'.format(parameter),
               'docker'])

    with open(os.path.join(image_dir, 'target', 'image.yaml'), 'r') as file_:
        effective_image = yaml.safe_load(file_)

    assert 'content_sets' not in effective_image['packages']
    assert "Finished!" in caplog.text


# https://github.com/cekit/cekit/issues/551
def test_validation_of_image_and_module_descriptors(tmpdir, mocker, caplog):
    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    run_cekit(image_dir, ['-v',
                          'build',
                          '--validate',
                          'docker'])

    assert "The --validate parameter was specified, generation will not be performed, exiting" in caplog.text


# https://github.com/cekit/cekit/issues/551
def test_validation_of_image_and_module_descriptors_should_fail_on_invalid_descriptor(tmpdir, mocker, caplog):
    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    descriptor = image_descriptor.copy()

    del descriptor['name']

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(descriptor, fd, default_flow_style=False)

    run_cekit_exception(image_dir, ['-v',
                                    'build',
                                    '--validate',
                                    'docker'])

    assert "Cannot validate schema: Image" in caplog.text
    assert "Cannot find required key 'name'" in caplog.text


def run_cekit(cwd,
              parameters=['build', '--dry-run', 'docker'],
              message=None):
    with Chdir(cwd):
        result = CliRunner().invoke(cli, parameters, catch_exceptions=False)
        assert result.exit_code == 0

        if message:
            assert message in result.output

        return result


def run_cekit_exception(cwd,
                        parameters=['-v', 'build', '--dry-run', 'docker'],
                        exit_code=1,
                        exception=SystemExit,
                        message=None):
    with Chdir(cwd):
        result = CliRunner().invoke(cli, parameters, catch_exceptions=False)

        assert isinstance(result.exception, exception)
        assert result.exit_code == exit_code

        if message:
            assert message in result.output
