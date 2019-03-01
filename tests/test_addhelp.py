# test the "addhelp" feature
# -*- encoding: utf-8 -*-
# we need to test cartesian product of:
#   cekit config {no addhelp, addhelp=True, addhelp=False}
#   cmdline      {nothing, --add-help, --no-add-help})

import os
import sys
import shutil
import yaml
import pytest
from cekit.tools import Chdir
from cekit.cli import Cekit, cli

from click.testing import CliRunner

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


def check_dockerfile_text(image_dir, match):
    with open(os.path.join(image_dir, 'target', 'image', 'Dockerfile'), 'r') as fd:
        dockerfile = fd.read()
        print("MATCH:\n{}".format(match))
        print("DOCKERFILE:\n{}".format(dockerfile))
        if match in dockerfile:
            return True
    return False


@pytest.fixture(scope="module")
def workdir(tmpdir_factory):
    tdir = str(tmpdir_factory.mktemp("image"))
    with open(os.path.join(tdir, 'image.yaml'), 'w') as fd:
        yaml.dump(image_descriptor, fd, default_flow_style=False)
    return tdir
    # XXX cleanup?


def run_cekit(cwd, args=['build', '--dry-run', 'docker']):
    with Chdir(cwd):
        return CliRunner().invoke(cli, args, catch_exceptions=False)


def setup_config(tmpdir, contents):
    p = str(tmpdir.join("config"))
    with open(p, 'w') as fd:
        fd.write(contents)
    return p


def cleanup(workdir):
    if os.path.exists('target'):
        shutil.rmtree('target')


def test_addhelp_mutex_cmdline(mocker, workdir, tmpdir):
    config = setup_config(tmpdir, '')
    result = run_cekit(workdir, ['-v', '--config', config,
                                 '--add-help', '--no-add-help', 'build', '--dry-run', 'docker'])

    assert isinstance(result.exception, SystemExit)
    assert result.exit_code == 2


def test_config_override_help_template(mocker, workdir, tmpdir):
    cleanup(workdir)
    help_template = os.path.join(workdir, "help.jinja")
    with open(help_template, "w") as fd:
        fd.write(template_teststr)
    config = setup_config(tmpdir, "[doc]\nhelp_template = {}".format(help_template))

    with Chdir(workdir):
        CliRunner().invoke(cli, ['-v', '--config', config, 'build',
                                 '--dry-run', 'docker'], catch_exceptions=False)

        with open("target/image/help.md", "r") as fd:
            contents = fd.read()
            assert contents.find(template_teststr) >= 0


def test_no_override_help_template(mocker, workdir, tmpdir):
    cleanup(workdir)
    config = setup_config(tmpdir, "")
    with Chdir(workdir):
        CliRunner().invoke(cli, ['-v', '--config', config, 'build',
                                 '--dry-run', 'docker'], catch_exceptions=False)
        with open("target/image/help.md", "r") as fd:
            contents = fd.read()
            assert -1 == contents.find(template_teststr)


def test_image_override_help_template(mocker, tmpdir):
    """Test that help_template defined in image.yaml is used for
       generating help.md"""

    help_template = os.path.join(str(tmpdir), "help.jinja")
    with open(help_template, "w") as fd:
        fd.write(template_teststr)

    config = setup_config(tmpdir, "")
    my_image_descriptor = image_descriptor.copy()
    my_image_descriptor['help'] = {'template': help_template}

    with Chdir(str(tmpdir)):
        with open('image.yaml', 'w') as fd:
            yaml.dump(my_image_descriptor, fd, default_flow_style=False)
        CliRunner().invoke(cli, ['-v', '--config', config, 'build',
                                 '--dry-run', 'docker'], catch_exceptions=False)
        with open("target/image/help.md", "r") as fd:
            contents = fd.read()
            assert contents.find(template_teststr) >= 0


def test_image_override_config_help_template(mocker, tmpdir):
    """Test that help_template defined in image.yaml overrides help_template
       defined in the config"""

    help_template1 = os.path.join(str(tmpdir), "help1.jinja")
    with open(help_template1, "w") as fd:
        fd.write("1")
    config = setup_config(tmpdir, "[doc]\nhelp_template = {}".format(help_template1))

    help_template2 = os.path.join(str(tmpdir), "help2.jinja")
    with open(help_template2, "w") as fd:
        fd.write("2")
    my_image_descriptor = image_descriptor.copy()
    my_image_descriptor['help'] = {'template': help_template2}

    with Chdir(str(tmpdir)):
        with open('image.yaml', 'w') as fd:
            yaml.dump(my_image_descriptor, fd, default_flow_style=False)
        CliRunner().invoke(cli, ['-v', '--config', config, 'build',
                                 '--dry-run', 'docker'], catch_exceptions=False)
        with open("target/image/help.md", "r") as fd:
            contents = fd.read()
            assert contents == "2"

# test method naming scheme:
#   test_confX_cmdlineY where {X,Y} ∈ {None,True,False}
# XXX: would be nicer to dynamically generate these


def test_confNone_cmdlineNone(mocker, workdir, tmpdir):
    config = setup_config(tmpdir, '')
    run_cekit(workdir, ['-v', '--config', config, 'build',
                        '--dry-run', 'docker'])
    assert os.path.exists(os.path.join(workdir, 'target', 'image', 'help.md'))
    assert check_dockerfile_text(workdir, 'ADD help.md /') == False


def test_confFalse_cmdlineNone(mocker, workdir, tmpdir):
    config = setup_config(tmpdir, "[doc]\naddhelp = False")
    run_cekit(workdir, ['-v', '--config', config, 'build',
                        '--dry-run', 'docker'])
    assert os.path.exists(os.path.join(workdir, 'target', 'image', 'help.md'))
    assert check_dockerfile_text(workdir, 'ADD help.md /') == False


def test_confTrue_cmdlineNone(mocker, workdir, tmpdir):
    config = setup_config(tmpdir, "[doc]\naddhelp = True")
    run_cekit(workdir, ['-v', '--config', config, 'build',
                        '--dry-run', 'docker'])
    assert os.path.exists(os.path.join(workdir, 'target', 'image', 'help.md'))
    assert check_dockerfile_text(workdir, 'ADD help.md /') == True


def test_confNone_cmdlineTrue(mocker, workdir, tmpdir):
    config = setup_config(tmpdir, '')
    run_cekit(workdir, ['-v', '--config', config, 'build', '--add-help', 'y',
                        '--dry-run', 'docker'])
    assert os.path.exists(os.path.join(workdir, 'target', 'image', 'help.md'))
    assert check_dockerfile_text(workdir, 'ADD help.md /') == True


def test_confFalse_cmdlineTrue(mocker, workdir, tmpdir):
    config = setup_config(tmpdir, "[doc]\naddhelp = False")
    run_cekit(workdir, ['-v', '--config', config, 'build', '--add-help', 'y',
                        '--dry-run', 'docker'])
    assert os.path.exists(os.path.join(workdir, 'target', 'image', 'help.md'))
    assert check_dockerfile_text(workdir, 'ADD help.md /') == True


def test_confTrue_cmdlineTrue(mocker, workdir, tmpdir):
    config = setup_config(tmpdir, "[doc]\naddhelp = True")
    run_cekit(workdir, ['-v', '--config', config, 'build', '--add-help', 'y',
                        '--dry-run', 'docker'])
    assert os.path.exists(os.path.join(workdir, 'target', 'image', 'help.md'))
    assert check_dockerfile_text(workdir, 'ADD help.md /') == True


def test_confNone_cmdlineFalse(mocker, workdir, tmpdir):
    config = setup_config(tmpdir, '')
    run_cekit(workdir, ['-v', '--config', config, 'build', '--add-help', 'n',
                        '--dry-run', 'docker'])
    assert os.path.exists(os.path.join(workdir, 'target', 'image', 'help.md'))
    assert check_dockerfile_text(workdir, 'ADD help.md /') == False


def test_confFalse_cmdlineFalse(mocker, workdir, tmpdir):
    config = setup_config(tmpdir, "[doc]\naddhelp = False")
    run_cekit(workdir, ['-v', '--config', config, 'build', '--add-help', 'n',
                        '--dry-run', 'docker'])
    assert os.path.exists(os.path.join(workdir, 'target', 'image', 'help.md'))
    assert check_dockerfile_text(workdir, 'ADD help.md /') == False


def test_confTrue_cmdlineFalse(mocker, workdir, tmpdir):
    config = setup_config(tmpdir, "[doc]\naddhelp = True")
    run_cekit(workdir, ['-v', '--config', config, 'build', '--add-help', 'n',
                        '--dry-run', 'docker'])
    assert os.path.exists(os.path.join(workdir, 'target', 'image', 'help.md'))
    assert check_dockerfile_text(workdir, 'ADD help.md /') == False
