# -*- encoding: utf-8 -*-

from __future__ import print_function

import os
import sys

import pytest
import yaml
from click.testing import CliRunner

from cekit.cli import cli
from cekit.tools import Chdir

image_descriptor = {
    "schema_version": 1,
    "from": "centos:7",
    "name": "test/image",
    "version": "1.0",
    "labels": [{"name": "foo", "value": "bar"}, {"name": "labela", "value": "a"}],
    "envs": [{"name": "baz", "value": "qux"}, {"name": "enva", "value": "a"}],
    "run": {"cmd": ["sleep", "60"]},
}

template_teststr_1 = "This string does not occur in the default help.md template."
template_teststr_2 = """
{{ from }}
A simple template with a substitution.
"""


def check_file_text(image_dir, match, filename="Dockerfile"):
    with open(os.path.join(image_dir, "target", "image", filename), "r") as fd:
        file_content = fd.read()
        if match in file_content:
            return True
    return False


def run_cekit(image_dir, args=None, descriptor=None):
    if args is None:
        args = ["build", "--dry-run", "docker"]

    if descriptor is None:
        descriptor = image_descriptor

    with Chdir(image_dir):
        with open("image.yaml", "w") as fd:
            yaml.dump(descriptor, fd, default_flow_style=False)

        result = CliRunner().invoke(cli, args, catch_exceptions=False)
        sys.stdout.write("\n")
        sys.stdout.write(result.output)

        assert result.exit_code == 0
        return result


@pytest.mark.parametrize("template_str", [template_teststr_1, template_teststr_2])
@pytest.mark.parametrize("path_type", ["absolute", "relative"])
def test_custom_help_template_path(tmpdir, path_type, template_str):
    help_template = os.path.join(str(tmpdir), "help.jinja")

    if path_type == "relative":
        help_template = "help.jinja"

    my_image_descriptor = image_descriptor.copy()
    my_image_descriptor["help"] = {"template": help_template, "add": True}

    with Chdir(str(tmpdir)):
        with open("help.jinja", "w") as fd:
            fd.write(template_str)

        with open("image.yaml", "w") as fd:
            yaml.dump(my_image_descriptor, fd, default_flow_style=False)

        result = CliRunner().invoke(
            cli, ["-v", "build", "--dry-run", "docker"], catch_exceptions=False
        )
        sys.stdout.write("\n")
        sys.stdout.write(result.output)

        with open("target/image/help.md", "r") as fd:
            contents = fd.read()
            if (
                "This string does not occur in the default help.md template"
                in template_str
            ):
                assert template_str in contents
            else:
                assert (
                    """centos:7
A simple template with a substitution."""
                    in contents
                )


def test_default_should_not_generate_help(tmpdir):
    tmpdir = str(tmpdir)
    run_cekit(tmpdir, ["-v", "build", "--dry-run", "docker"])
    assert os.path.exists(os.path.join(tmpdir, "target", "image", "help.md")) is False


def test_should_generate_help_if_enabled_in_descriptor(tmpdir):
    """Uses default template"""
    tmpdir = str(tmpdir)

    my_image_descriptor = image_descriptor.copy()
    my_image_descriptor["help"] = {"add": True}

    print(
        run_cekit(
            tmpdir,
            ["-v", "build", "--dry-run", "docker"],
            descriptor=my_image_descriptor,
        ).output
    )
    assert os.path.exists(os.path.join(tmpdir, "target", "image", "help.md"))
    assert check_file_text(tmpdir, "# `test/image:1.0`", "help.md") is True
    assert (
        check_file_text(tmpdir, "Container will run as `root` user.", "help.md") is True
    )
    assert check_file_text(tmpdir, "There are no defined ports.", "help.md") is True
    assert check_file_text(tmpdir, "There are no volumes defined.", "help.md") is True
    assert (
        check_file_text(
            tmpdir, "This image is based on the `centos:7` image.", "help.md"
        )
        is True
    )
    assert (
        check_file_text(
            tmpdir, "There is no entrypoint specified for the container.", "help.md"
        )
        is True
    )


def test_should_generate_help_if_enabled_from_file(tmpdir):
    """Uses default template"""
    tmpdir = str(tmpdir)

    with Chdir(str(tmpdir)):
        with open("help.md", "w") as fd:
            fd.write(
                """# Markdown Heading
And more text"""
            )

        my_image_descriptor = image_descriptor.copy()
        my_image_descriptor["help"] = {"add": True, "template": "help.md"}

        run_cekit(
            tmpdir,
            ["-v", "build", "--dry-run", "docker"],
            descriptor=my_image_descriptor,
        )
    assert os.path.exists(os.path.join(tmpdir, "target", "image", "help.md"))
    assert check_file_text(tmpdir, "Markdown Heading", "help.md") is True
