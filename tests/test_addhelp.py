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
from cekit.builders.osbs import Chdir
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
    # XXX cleanup?

def run_cekit(cwd):
    with Chdir(cwd):
        c = Cekit().parse()
        c.configure()
        return c.generator._params['addhelp']

def setup_config(tmpdir, contents):
    p = str(tmpdir.join("config"))
    with open(p, 'w') as fd:
        fd.write(contents)
    return p

def test_addhelp_mutex_cmdline(mocker, workdir, tmpdir):
    config = setup_config(tmpdir, '')
    mocker.patch.object(sys, 'argv', ['cekit', '-v', '--config', config, '--add-help', '--no-add-help', 'generate'])
    with pytest.raises(SystemExit) as excinfo:
        run_cekit(workdir)
    assert 0 != excinfo.value.code

template_teststr = "This string does not occur in the default help.md template."

def cleanup(workdir):
    if os.path.exists('target'):
        shutil.rmtree('target')

def test_config_override_help_template(mocker, workdir, tmpdir):
    cleanup(workdir)
    help_template = os.path.join(workdir,"help.jinja")
    with open(help_template, "w") as fd:
        fd.write(template_teststr)
    config = setup_config(tmpdir, "[doc]\nhelp_template = {}".format(help_template))

    mocker.patch.object(sys, 'argv', ['cekit', '-v', '--config', config, 'generate'])
    with Chdir(workdir):
        c = Cekit().parse()
        c.configure()
        try:
            c.run()
        except SystemExit:
            pass
        with open("target/image/help.md", "r") as fd:
            contents = fd.read()
            assert contents.find(template_teststr) >= 0

def test_no_override_help_template(mocker, workdir, tmpdir):
    cleanup(workdir)
    config = setup_config(tmpdir, "")
    mocker.patch.object(sys, 'argv', ['cekit', '-v', '--config', config, 'generate'])
    with Chdir(workdir):
        c = Cekit().parse()
        c.configure()
        try:
            c.run()
        except SystemExit:
            pass
        with open("target/image/help.md", "r") as fd:
            contents = fd.read()
            sys.stderr.write("JMTD: {}\n".format(contents.find(template_teststr)))
            assert -1 == contents.find(template_teststr)

def test_image_override_help_template(mocker, tmpdir):
    help_template = os.path.join(str(tmpdir),"help.jinja")
    with open(help_template, "w") as fd:
        fd.write(template_teststr)

    config = setup_config(tmpdir, "")
    my_image_descriptor = image_descriptor.copy()
    my_image_descriptor['help_template'] = help_template
    mocker.patch.object(sys, 'argv', ['cekit', '-v', '--config', config, 'generate'])

    with Chdir(str(tmpdir)):
        with open('image.yaml', 'w') as fd:
            yaml.dump(my_image_descriptor, fd, default_flow_style=False)
        c = Cekit().parse()
        c.configure()
        try:
            c.run()
        except SystemExit:
            pass
        with open("target/image/help.md", "r") as fd:
            contents = fd.read()
            assert contents.find(template_teststr) >= 0

# test method naming scheme:
#   test_confX_cmdlineY where {X,Y} ∈ {None,True,False}
# XXX: would be nicer to dynamically generate these

def test_confNone_cmdlineNone(mocker, workdir, tmpdir):
    config = setup_config(tmpdir, '')
    mocker.patch.object(sys, 'argv', ['cekit', '-v', '--config', config, 'generate'])
    assert False == run_cekit(workdir)

def test_confFalse_cmdlineNone(mocker, workdir, tmpdir):
    config = setup_config(tmpdir, "[doc]\naddhelp = False")
    mocker.patch.object(sys, 'argv', ['cekit', '-v', '--config', config, 'generate'])
    assert False == run_cekit(workdir)

def test_confTrue_cmdlineNone(mocker, workdir, tmpdir):
    config = setup_config(tmpdir, "[doc]\naddhelp = True")
    mocker.patch.object(sys, 'argv', ['cekit', '-v', '--config', config, 'generate'])
    assert True == run_cekit(workdir)

def test_confNone_cmdlineTrue(mocker, workdir, tmpdir):
    config = setup_config(tmpdir, '')
    mocker.patch.object(sys, 'argv', ['cekit', '-v', '--config', config, '--add-help', 'generate'])
    assert True == run_cekit(workdir)

def test_confFalse_cmdlineTrue(mocker, workdir, tmpdir):
    config = setup_config(tmpdir, "[doc]\naddhelp = False")
    mocker.patch.object(sys, 'argv', ['cekit', '-v', '--config', config, '--add-help', 'generate'])
    assert True == run_cekit(workdir)

def test_confTrue_cmdlineTrue(mocker, workdir, tmpdir):
    config = setup_config(tmpdir, "[doc]\naddhelp = True")
    mocker.patch.object(sys, 'argv', ['cekit', '-v', '--config', config, '--add-help', 'generate'])
    assert True == run_cekit(workdir)

def test_confNone_cmdlineFalse(mocker, workdir, tmpdir):
    config = setup_config(tmpdir, '')
    mocker.patch.object(sys, 'argv', ['cekit', '-v', '--config', config, '--no-add-help', 'generate'])
    assert False == run_cekit(workdir)

def test_confFalse_cmdlineFalse(mocker, workdir, tmpdir):
    config = setup_config(tmpdir, "[doc]\naddhelp = False")
    mocker.patch.object(sys, 'argv', ['cekit', '-v', '--config', config, '--no-add-help', 'generate'])
    assert False == run_cekit(workdir)

def test_confTrue_cmdlineFalse(mocker, workdir, tmpdir):
    config = setup_config(tmpdir, "[doc]\naddhelp = True")
    mocker.patch.object(sys, 'argv', ['cekit', '-v', '--config', config, '--no-add-help', 'generate'])
    assert False == run_cekit(workdir)
