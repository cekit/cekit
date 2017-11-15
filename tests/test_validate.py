import os
import sys
import yaml

import pytest
from concreate.builders.osbs import Chdir
from concreate.cli import Concreate

image_descriptor = {
    'schema_version': 1,
    'from': 'busybox:latest',
    'name': 'test/busybox',
    'version': '1.0',
    'labels': [{'name': 'foo', 'value': 'bar'}, {'name': 'labela', 'value': 'a'}],
    'run': {'cmd': ['sleep', '60']}
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


def test_simple_image_build(tmpdir, mocker):
    mocker.patch.object(sys, 'argv', ['concreate',
                                      '-v',
                                      'build'])

    image_dir = str(tmpdir.mkdir('source'))

    with open(os.path.join(image_dir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)

    run_concreate(image_dir)


def test_simple_image_test(tmpdir, mocker):
    mocker.patch.object(sys, 'argv', ['concreate', '-v',
                                      'build',
                                      'test'])

    image_dir = str(tmpdir.mkdir('source'))

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


def run_concreate(cwd):
    with Chdir(cwd):
        # run concreate and check it exits with 0
        with pytest.raises(SystemExit) as system_exit:
            Concreate().parse().run()
        assert system_exit.value.code == 0
