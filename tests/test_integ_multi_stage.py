# -*- encoding: utf-8 -*-

from __future__ import print_function

import os
import shutil
import yaml
import pytest

from click.testing import CliRunner

from cekit.tools import Chdir
from cekit.cli import cli

image_descriptor = {
    'schema_version': 1,
    'from': 'centos:latest',
    'name': 'test/image',
    'version': '1.0',
    'labels': [{'name': 'foo', 'value': 'bar'}, {'name': 'labela', 'value': 'a'}],
    'envs': [{'name': 'baz', 'value': 'qux'}, {'name': 'enva', 'value': 'a'}],
    'run': {'cmd': ['sleep', '60']},
}

template_teststr = "This string does not occur in the default help.md template."


def check_file_text(image_dir, match, filename="Dockerfile"):
    with open(os.path.join(image_dir, 'target', 'image', filename), 'r') as fd:
        file_content = fd.read()
        if match in file_content:
            return True
    return False


def run_cekit(image_dir, args=None):
    if args is None:
        args = ['build', '--dry-run', 'docker']

    with Chdir(image_dir):
        result = CliRunner().invoke(cli, args, catch_exceptions=False)
        assert result.exit_code == 0
        return result


def test_multi_stage_single_image_in_list(tmpdir):
    """
    Build simple image which is a regular image, but the
    difference is that it is defined in an array in image
    descriptor
    """
    tmpdir = str(tmpdir)

    with open(os.path.join(tmpdir, 'image.yaml'), 'w') as fd:
        yaml.dump([image_descriptor], fd, default_flow_style=False)

    run_cekit(tmpdir, ['-v', 'build', 'docker'])
    
    assert os.path.exists(os.path.join(tmpdir, 'target', 'image', 'Dockerfile')) is True
    assert check_file_text(tmpdir, 'ADD help.md /') is False

def test_multi_stage_proper_image(tmpdir):
    """
    Build simple image which is a regular image, but the
    difference is that it is defined in an array in image
    descriptor
    """
    tmpdir = str(tmpdir)

    shutil.copytree(
        os.path.join(os.path.dirname(__file__), 'images', 'multi-stage'),
        os.path.join(tmpdir, 'multi-stage')
    )

    run_cekit(os.path.join(tmpdir, 'multi-stage'), ['-v', 'build', 'podman'])