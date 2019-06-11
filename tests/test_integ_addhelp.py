# -*- encoding: utf-8 -*-

from __future__ import print_function

import os
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
       # print("MATCH:\n{}".format(match))
       # print("FILE:\n{}".format(file_content))
        if match in file_content:
            return True
    return False


def run_cekit(image_dir, args=None, descriptor=None):
    if args is None:
        args = ['build', '--dry-run', 'docker']

    if descriptor is None:
        descriptor = image_descriptor

    with Chdir(image_dir):
        with open('image.yaml', 'w') as fd:
            yaml.dump(descriptor, fd, default_flow_style=False)

        result = CliRunner().invoke(cli, args, catch_exceptions=False)
        assert result.exit_code == 0
        return result


def setup_config(tmpdir, contents):
    p = str(tmpdir.join("config"))
    with open(p, 'w') as fd:
        fd.write(contents)
    return p


@pytest.mark.parametrize('path_type', [
    'absolute', 'relative'
])
def test_custom_help_template_path(tmpdir, path_type):
    help_template = os.path.join(str(tmpdir), "help.jinja")

    if path_type == 'relative':
        help_template = "help.jinja"

    my_image_descriptor = image_descriptor.copy()
    my_image_descriptor['help'] = {'template': help_template, 'add': True}

    with Chdir(str(tmpdir)):
        with open('help.jinja', "w") as fd:
            fd.write(template_teststr)

        with open('image.yaml', 'w') as fd:
            yaml.dump(my_image_descriptor, fd, default_flow_style=False)

        CliRunner().invoke(cli, ['-v', 'build', '--dry-run', 'docker'], catch_exceptions=False)

        with open("target/image/help.md", "r") as fd:
            contents = fd.read()
            assert contents.find(template_teststr) >= 0


def test_default_should_not_generate_help(tmpdir):
    tmpdir = str(tmpdir)
    run_cekit(tmpdir, ['-v', 'build', '--dry-run', 'docker'])
    assert os.path.exists(os.path.join(tmpdir, 'target', 'image', 'help.md')) is False
    assert check_file_text(tmpdir, 'ADD help.md /') is False


def test_should_generate_help_if_enabled_in_descriptor(tmpdir):
    """ Uses default template """
    tmpdir = str(tmpdir)

    my_image_descriptor = image_descriptor.copy()
    my_image_descriptor['help'] = {'add': True}

    print(run_cekit(tmpdir, ['-v', 'build', '--dry-run', 'docker'],
                    descriptor=my_image_descriptor).output)
    assert os.path.exists(os.path.join(tmpdir, 'target', 'image', 'help.md'))
    assert check_file_text(tmpdir, 'ADD help.md /') is True
    assert check_file_text(tmpdir, '# test/image', 'help.md') is True
    assert check_file_text(tmpdir, "The container runs as root", 'help.md') is True
