import os
import shutil
import sys

import yaml
import pytest

from cekit.builders.osbs import Chdir
from cekit.errors import CekitError
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

    assert "Cannot fetch Artifact: 'aaa', please cache it via cekit-cache." in caplog.text


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

    expected_modules_order = """# Custom scripts
USER root
RUN [ "bash", "-x", "/tmp/scripts/child_of_child/script_d" ]

USER root
RUN [ "bash", "-x", "/tmp/scripts/child2_of_child/scripti_e" ]

USER root
RUN [ "bash", "-x", "/tmp/scripts/child3_of_child/script_f" ]

USER root
RUN [ "bash", "-x", "/tmp/scripts/child/script_b" ]

USER root
RUN [ "bash", "-x", "/tmp/scripts/child_2/script_c" ]

USER root
RUN [ "bash", "-x", "/tmp/scripts/child_of_child3/script_g" ]

USER root
RUN [ "bash", "-x", "/tmp/scripts/child2_of_child3/script_h" ]

USER root
RUN [ "bash", "-x", "/tmp/scripts/master/script_a" ]

USER root
RUN rm -rf /tmp/scripts
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

    expected_modules_order = """# Custom scripts
USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_1/a" ]

USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_1/b" ]

USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_1/c" ]

USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_2/a" ]

USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_2/b" ]

USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_2/c" ]

USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_3/a" ]

USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_3/b" ]

USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_3/c" ]

USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_4/a" ]

USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_4/b" ]

USER root
RUN [ "bash", "-x", "/tmp/scripts/mod_4/c" ]

USER root
RUN rm -rf /tmp/scripts
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

