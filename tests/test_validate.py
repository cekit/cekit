import os
import shutil
import sys

import subprocess
import yaml
import pytest

from cekit.tools import Chdir
from cekit.descriptor import Repository
from cekit.cli import Cekit

#pytestmark = pytest.mark.skipif('CEKIT_TEST_VALIDATE' not in os.environ, reason="Tests require "
#                                "Docker installed, export 'CEKIT_TEST_VALIDATE=y' variable if "
#                                "you need to run them.")


def setup_function():
    """Reload cekit.module to make sure it doesnt contain old modules instances"""
    import cekit.module
    try:
        from imp import reload
    except NameError:
        from importlib import reload

    reload(cekit.module)


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


def run_cekit_cs_overrides(image_dir, mocker, overrides_descriptor):
    mocker.patch.object(sys, 'argv', ['cekit',
                                      '--config',
                                      'config',
                                      '--overrides',
                                      'overrides.yaml',
                                      '-v',
                                      'generate'])

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

    run_cekit(image_dir)

def test_content_sets_file_container_file(tmpdir, mocker, caplog):
    # Do not try to validate dependencies while running tests, these are not neccessary
    mocker.patch('cekit.generator.docker.DockerGenerator.dependencies').return_value({})
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

    assert "Creating ODCS content set via 'odcs --redhat create pulp aaa bbb'" in caplog.text
    assert "The image has ContentSets repositories specified, all other repositories are removed!" in caplog.text

def test_content_sets_file_container_embedded(tmpdir, mocker, caplog):
    # Do not try to validate dependencies while running tests, these are not neccessary
    mocker.patch('cekit.generator.docker.DockerGenerator.dependencies').return_value({})
    overrides_descriptor = {
        'schema_version': 1,
        'packages': {'content_sets_file': 'content_sets.yml'},
        'osbs': {'configuration': {'container': {'compose': {'pulp_repos': True}}}}}

    content_sets = {'x86_64': ['aaa', 'bbb']}

    image_dir = str(tmpdir.mkdir('source'))

    with open(os.path.join(image_dir, 'content_sets.yml'), 'w') as fd:
        yaml.dump(content_sets, fd, default_flow_style=False)

    run_cekit_cs_overrides(image_dir, mocker, overrides_descriptor)

    assert "Creating ODCS content set via 'odcs --redhat create pulp aaa bbb'" in caplog.text
    assert "The image has ContentSets repositories specified, all other repositories are removed!" in caplog.text

def test_content_sets_embedded_container_embedded(tmpdir, mocker, caplog):
    # Do not try to validate dependencies while running tests, these are not neccessary
    mocker.patch('cekit.generator.docker.DockerGenerator.dependencies').return_value({})
    overrides_descriptor = {
        'schema_version': 1,
        'packages': {'content_sets': {'x86_64': ['aaa', 'bbb']}},
        'osbs': {'configuration': {'container': {'compose': {'pulp_repos': True}}}}}

    image_dir = str(tmpdir.mkdir('source'))

    run_cekit_cs_overrides(image_dir, mocker, overrides_descriptor)

    assert "Creating ODCS content set via 'odcs --redhat create pulp aaa bbb'" in caplog.text
    assert "The image has ContentSets repositories specified, all other repositories are removed!" in caplog.text

def test_content_sets_embedded_container_file(tmpdir, mocker, caplog):
    # Do not try to validate dependencies while running tests, these are not neccessary
    mocker.patch('cekit.generator.docker.DockerGenerator.dependencies').return_value({})
    overrides_descriptor = {
        'schema_version': 1,
        'packages': {'content_sets': {'x86_64': ['aaa', 'bbb']}},
        'osbs': {'configuration': {'container_file': 'container.yaml'}}}

    image_dir = str(tmpdir.mkdir('source'))
    container = {'compose': {'pulp_repos': True}}

    with open(os.path.join(image_dir, 'container.yaml'), 'w') as fd:
        yaml.dump(container, fd, default_flow_style=False)

    run_cekit_cs_overrides(image_dir, mocker, overrides_descriptor)

    assert "Creating ODCS content set via 'odcs --redhat create pulp aaa bbb'" in caplog.text
    assert "The image has ContentSets repositories specified, all other repositories are removed!" in caplog.text

def copy_repos(dst):
    shutil.copytree(os.path.join(os.path.dirname(__file__),
                                 'modules'),
                    os.path.join(dst, 'tests', 'modules'))


def test_simple_image_build(tmpdir, mocker):
    mocker.patch.object(sys, 'argv', ['cekit',
                                      '-v',
                                      'build'])

    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    run_cekit(image_dir)


def test_simple_image_test(tmpdir, mocker):
    mocker.patch.object(sys, 'argv', ['cekit', '-v',
                                      'test'])

    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    feature_files = os.path.join(image_dir, 'tests', 'features', 'test.feature')

    os.makedirs(os.path.dirname(feature_files))

    with open(feature_files, 'w') as fd:
        fd.write(feature_label_test)

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    run_cekit(image_dir)

    assert os.path.exists(os.path.join(image_dir, 'target', 'image'))
    assert not os.path.exists(os.path.join(image_dir, 'target', 'image', 'Dockerfile'))


def test_image_generate_with_multiple_overrides(tmpdir, mocker):
    override1 = "{'labels': [{'name': 'foo', 'value': 'bar'}]}"

    override2 = "{'labels': [{'name': 'foo', 'value': 'baz'}]}"

    mocker.patch.object(sys, 'argv', ['cekit',
                                      '--overrides',
                                      override1,
                                      '--overrides',
                                      override2,
                                      '-v',
                                      'generate'])

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

    run_cekit(image_dir)

    effective_image = {}
    with open(os.path.join(image_dir, 'target', 'image.yaml'), 'r') as file_:
        effective_image = yaml.safe_load(file_)

    assert {'name': 'foo', 'value': 'baz'} in effective_image['labels']


def test_image_test_with_override(tmpdir, mocker):
    mocker.patch.object(sys, 'argv', ['cekit',
                                      '--overrides',
                                      'overrides.yaml',
                                      '-v',
                                      'build',
                                      'test'])

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

    run_cekit(image_dir)

    effective_image = {}
    with open(os.path.join(image_dir, 'target', 'image.yaml'), 'r') as file_:
        effective_image = yaml.safe_load(file_)

    assert {'name': 'foo', 'value': 'overriden'} in effective_image['labels']


def test_image_test_with_multiple_overrides(tmpdir, mocker):
    mocker.patch.object(sys, 'argv', ['cekit',
                                      '--overrides-file',
                                      'overrides.yaml',
                                      '--overrides-file',
                                      'overrides2.yaml',
                                      '--overrides',
                                      "{'labels': [{'name': 'foo', 'value': 'overriden'}]}",
                                      '-v',
                                      'build',
                                      'test'])

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

    run_cekit(image_dir)

    effective_image = {}
    with open(os.path.join(image_dir, 'target', 'image.yaml'), 'r') as file_:
        effective_image = yaml.safe_load(file_)

    assert {'name': 'foo', 'value': 'overriden'} in effective_image['labels']


def test_image_test_with_override_on_cmd(tmpdir, mocker):
    overrides_descriptor = "{'labels': [{'name': 'foo', 'value': 'overriden'}]}"
    mocker.patch.object(sys, 'argv', ['cekit',
                                      '--overrides',
                                      overrides_descriptor,
                                      '-v',
                                      'build',
                                      'test'])

    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    feature_files = os.path.join(image_dir, 'tests', 'features', 'test.feature')

    os.makedirs(os.path.dirname(feature_files))

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    with open(feature_files, 'w') as fd:
        fd.write(feature_label_test_overriden)

    run_cekit(image_dir)


def test_module_override(tmpdir, mocker):
    mocker.patch.object(sys, 'argv', ['cekit',
                                      '--overrides',
                                      'overrides.yaml',
                                      '-v',
                                      'generate'])

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

    run_cekit(image_dir)

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


def check_dockerfile(image_dir, match):
    with open(os.path.join(image_dir, 'target', 'image', 'Dockerfile'), 'r') as fd:
        for line in fd.readlines():
            if line.strip() == match.strip():
                return True
    return False


def check_dockerfile_text(image_dir, match):
    with open(os.path.join(image_dir, 'target', 'image', 'Dockerfile'), 'r') as fd:
        dockerfile = fd.read()
        print(match)
        print(dockerfile)
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


def test_local_module_injection(tmpdir, mocker):
    mocker.patch.object(sys, 'argv', ['cekit',
                                      'generate'])

    image_dir = str(tmpdir.mkdir('source'))

    local_desc = image_descriptor.copy()
    local_desc['modules'] = {'install': [{'name': 'foo'}]}

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(local_desc, fd, default_flow_style=False)

    shutil.copytree(os.path.join(os.path.dirname(__file__),
                                 'modules', 'repo_1'),
                    os.path.join(image_dir, 'modules'))
    run_cekit(image_dir)
    assert os.path.exists(os.path.join(image_dir,
                                       'target',
                                       'image',
                                       'modules',
                                       'foo',
                                       'original'))


def test_local_module_not_injected(tmpdir, mocker):
    mocker.patch.object(sys, 'argv', ['cekit',
                                      'generate'])

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


def test_run_override_user(tmpdir, mocker):
    mocker.patch.object(sys, 'argv', ['cekit',
                                      '--overrides',
                                      'overrides.yaml',
                                      '-v',
                                      'generate'])

    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    overrides_descriptor = {
        'schema_version': 1,
        'run': {'user': '4321'}}

    with open(os.path.join(image_dir, 'overrides.yaml'), 'w') as fd:
        yaml.dump(overrides_descriptor, fd, default_flow_style=False)

    run_cekit(image_dir)

    assert check_dockerfile(image_dir, 'USER 4321')


def test_run_override_artifact(tmpdir, mocker):
    mocker.patch.object(sys, 'argv', ['cekit',
                                      '--overrides',
                                      'overrides.yaml',
                                      '-v',
                                      'generate'])

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

    run_cekit(image_dir)

    assert check_dockerfile_uniq(image_dir, 'bar.jar \\')


def test_run_path_artifact_brew(tmpdir, mocker, caplog):
    mocker.patch.object(sys, 'argv', ['cekit',
                                      '-v',
                                      'generate'])

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


def test_run_path_artifact_target(tmpdir, mocker):
    mocker.patch.object(sys, 'argv', ['cekit',
                                      '-v',
                                      'generate'])

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


def test_execution_order(tmpdir, mocker):
    mocker.patch.object(sys, 'argv', ['cekit',
                                      '-v',
                                      'generate'])

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
# begin child_of_child:None

# Environment variables
ENV \\
    foo="child_of_child" 

# Custom scripts
USER root
RUN [ "bash", "-x", "/tmp/scripts/child_of_child/script_d" ]

# end child_of_child:None

# begin child2_of_child:None

# Custom scripts
USER root
RUN [ "bash", "-x", "/tmp/scripts/child2_of_child/scripti_e" ]

# end child2_of_child:None

# begin child3_of_child:None

# Custom scripts
USER root
RUN [ "bash", "-x", "/tmp/scripts/child3_of_child/script_f" ]

# end child3_of_child:None

# begin child:None

# Environment variables
ENV \\
    foo="child" 

# Custom scripts
USER root
RUN [ "bash", "-x", "/tmp/scripts/child/script_b" ]

# end child:None

# begin child_2:None

# Custom scripts
USER root
RUN [ "bash", "-x", "/tmp/scripts/child_2/script_c" ]

# end child_2:None

# begin child_of_child3:None

# Custom scripts
USER root
RUN [ "bash", "-x", "/tmp/scripts/child_of_child3/script_g" ]

# end child_of_child3:None

# begin child2_of_child3:None

# Custom scripts
USER root
RUN [ "bash", "-x", "/tmp/scripts/child2_of_child3/script_h" ]

# end child2_of_child3:None

# begin child_3:None

# end child_3:None

# begin master:None

# Environment variables
ENV \\
    foo="master" 

# Custom scripts
USER root
RUN [ "bash", "-x", "/tmp/scripts/master/script_a" ]

# end master:None
"""
    assert check_dockerfile_text(image_dir, expected_modules_order)


def test_override_modules_child(tmpdir, mocker):
    mocker.patch.object(sys, 'argv', ['cekit',
                                      '-v',
                                      'generate'])

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
    mocker.patch.object(sys, 'argv', ['cekit',
                                      '-v',
                                      'generate'])

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


def test_execution_order_flat(tmpdir, mocker):
    mocker.patch.object(sys, 'argv', ['cekit',
                                      '-v',
                                      'generate'])

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
# begin mod_1:None

# Environment variables
ENV \\
    foo="mod_1" 

# Custom scripts
USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_1/a" ]
USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_1/b" ]
USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_1/c" ]

# end mod_1:None

# begin mod_2:None

# Environment variables
ENV \\
    foo="mod_2" 

# Custom scripts
USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_2/a" ]
USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_2/b" ]
USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_2/c" ]

# end mod_2:None

# begin mod_3:None

# Custom scripts
USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_3/a" ]
USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_3/b" ]
USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_3/c" ]

# end mod_3:None

# begin mod_4:None

# Custom scripts
USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_4/a" ]
USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_4/b" ]
USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_4/c" ]

# end mod_4:None
"""
    assert check_dockerfile_text(image_dir, expected_modules_order)


def run_cekit(cwd):
    with Chdir(cwd):
        # run cekit and check it exits with 0
        with pytest.raises(SystemExit) as system_exit:
            Cekit().parse().run()
        assert system_exit.value.code == 0


def run_cekit_exception(cwd):
    with Chdir(cwd):
        # run cekit and check it exits with 0
        with pytest.raises(SystemExit) as system_exit:
            Cekit().parse().run()
        assert system_exit.value.code == 1

