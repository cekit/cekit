import os
import pytest
import re

from cekit.generator import Generator
from cekit.descriptor import Module
from cekit.version import version as cekit_version

basic_config = {'release': 1,
                'version': 1,
                'from': 'scratch',
                'name': 'testimage'}


def print_test_name(value):
    if str(value).startswith('test'):
        return value
    return "\b"


@pytest.mark.parametrize('name, desc_part, exp_regex', [
    ('test_run_user',
     {'run': {'user': 1347, 'cmd': ['whoami']}}, r'.*USER 1347\n+.*CMD.*'),
    ('test_default_run_user',
     {'run': {'cmd': ['whatever']}},  r'.*USER root\n+.*CMD.*'),
    ('test_custom_cmd',
     {'run': {'cmd': ['/usr/bin/date']}}, r'.*CMD \["/usr/bin/date"\]'),
    ('test_entrypoint',
     {'run': {'entrypoint': ['/usr/bin/date']}}, r'.*ENTRYPOINT \["/usr/bin/date"\]'),
    ('test_workdir',
     {'run': {'workdir': '/home/jboss'}}, r'.*WORKDIR /home/jboss'),
    ('test_volumes',
     {'volumes': [{'path': '/var/lib'},
                  {'path': '/usr/lib',
                   'name': 'path.lib'}]}, r'.*VOLUME \["/var/lib"\]\nVOLUME \["/usr/lib"\]'),
    ('test_ports',
     {'ports': [{'value': 8080},
                {'expose': False,
                 'value': 9999}]}, r'.*EXPOSE 8080$'),
    ('test_env', {'envs':  [{'name': 'CONFIG_ENV',
                             'example': 1234},
                            {'name': 'COMBINED_ENV',
                             'value': 'set_value',
                             'example': 'example_value',
                             'description': 'This is a description'}]},
     r'ENV JBOSS_IMAGE_NAME=\"testimage\" \\\s+JBOSS_IMAGE_VERSION=\"1\" \\\s+COMBINED_ENV=\"set_value\" \n'),
    ('test_execute',
     {'execute': [{'script': 'foo_script'}]},
     r'.*RUN [ "bash", "-x", "/tmp/scripts/testimage/foo_script" ].*'),
    ('test_execute_user',
     {'execute': [{'script': 'bar_script',
                   'user': 'bar_user'}]},
     r'.*USER bar_user\n+RUN [ "bash", "-x", "/tmp/scripts/testimage/foo_script" ].*'),
    ('test_concrt_label_version',
     {},
     r'.*org.concrt.version="%s".*' % cekit_version),
    ('test_cekit_label_version',
     {},
     r'.*io.cekit.version="%s".*' % cekit_version)],
                         ids=print_test_name)
def test_dockerfile_rendering(tmpdir, name, desc_part, exp_regex):

    target = str(tmpdir.mkdir('target'))

    generator = prepare_generator(target, desc_part)
    generator.render_dockerfile()

    regex_dockerfile(target, exp_regex)


@pytest.mark.parametrize('name, desc_part, exp_regex', [
    ('test_without_family',
     {}, r'ENV JBOSS_IMAGE_NAME=\"testimage-tech-preview\"'),
    ('test_with_family',
        {'name': 'testimage/test'}, r'ENV JBOSS_IMAGE_NAME=\"testimage-tech-preview/test\"')],
                         ids=print_test_name)
def test_dockerfile_rendering_tech_preview(tmpdir, name, desc_part, exp_regex):
    target = str(tmpdir.mkdir('target'))
    generator = prepare_generator(target, desc_part)
    generator.generate_tech_preview()
    generator.render_dockerfile()
    regex_dockerfile(target, exp_regex)


def prepare_generator(target, desc_part, desc_type="image"):
    # create basic descriptor

    desc = basic_config.copy()
    desc.update(desc_part)

    image = Module(desc, '/tmp/')

    generator = Generator.__new__(Generator)
    generator.image = image
    generator.target = target
    return generator


def regex_dockerfile(target, exp_regex):
    with open(os.path.join(target, 'image', 'Dockerfile'), "r") as fd:
        dockerfile_content = fd.read()
        regex = re.compile(exp_regex, re.MULTILINE)
        assert regex.search(dockerfile_content)
