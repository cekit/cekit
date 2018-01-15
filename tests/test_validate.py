import os
import shutil
import sys

import yaml
import pytest

from concreate.builders.osbs import Chdir
from concreate.cli import Concreate


def setup_function():
    """Reload concreate.module to make sure it doesnt contain old modules instances"""
    import concreate.module
    try:
        from imp import reload
    except NameError:
        from importlib import reload

    reload(concreate.module)


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
    mocker.patch.object(sys, 'argv', ['concreate',
                                      '-v',
                                      'build'])

    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    run_concreate(image_dir)


def test_simple_image_test(tmpdir, mocker):
    mocker.patch.object(sys, 'argv', ['concreate', '-v',
                                      'build',
                                      'test'])

    image_dir = str(tmpdir.mkdir('source'))
    copy_repos(image_dir)

    feature_files = os.path.join(image_dir, 'tests', 'features', 'test.feature')

    os.makedirs(os.path.dirname(feature_files))

    with open(feature_files, 'w') as fd:
        fd.write(feature_label_test)

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    run_concreate(image_dir)


def test_image_test_with_override(tmpdir, mocker):
    mocker.patch.object(sys, 'argv', ['concreate',
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

    run_concreate(image_dir)


def test_image_test_with_override_on_cmd(tmpdir, mocker):
    overrides_descriptor = "{'labels': [{'name': 'foo', 'value': 'overriden'}]}"
    mocker.patch.object(sys, 'argv', ['concreate',
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

    run_concreate(image_dir)


def test_module_override(tmpdir, mocker):
    mocker.patch.object(sys, 'argv', ['concreate',
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

    run_concreate(image_dir)

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


def test_local_module_injection(tmpdir, mocker):
    mocker.patch.object(sys, 'argv', ['concreate',
                                      'generate'])

    image_dir = str(tmpdir.mkdir('source'))

    local_desc = image_descriptor.copy()
    local_desc['modules'] = {'install': [{'name': 'foo'}]}

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(local_desc, fd, default_flow_style=False)

    shutil.copytree(os.path.join(os.path.dirname(__file__),
                                 'modules', 'repo_1'),
                    os.path.join(image_dir, 'modules'))
    run_concreate(image_dir)
    assert os.path.exists(os.path.join(image_dir,
                                       'target',
                                       'image',
                                       'modules',
                                       'foo',
                                       'original'))


def test_local_module_not_injected(tmpdir, mocker):
    mocker.patch.object(sys, 'argv', ['concreate',
                                      'generate'])

    image_dir = str(tmpdir.mkdir('source'))

    local_desc = image_descriptor.copy()
    local_desc.pop('modules')

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(local_desc, fd, default_flow_style=False)

    shutil.copytree(os.path.join(os.path.dirname(__file__),
                                 'modules', 'repo_1'),
                    os.path.join(image_dir, 'modules'))
    run_concreate(image_dir)
    assert not os.path.exists(os.path.join(image_dir,
                                           'target',
                                           'image',
                                           'modules'))


def test_run_override_user(tmpdir, mocker):
    mocker.patch.object(sys, 'argv', ['concreate',
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

    run_concreate(image_dir)

    assert check_dockerfile(image_dir, 'USER 4321')


def run_concreate(cwd):
    with Chdir(cwd):
        # run concreate and check it exits with 0
        with pytest.raises(SystemExit) as system_exit:
            Concreate().parse().run()
        assert system_exit.value.code == 0
