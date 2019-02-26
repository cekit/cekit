import os
import re
import subprocess

import pytest
import yaml

from cekit.config import Config
from cekit.descriptor import Repository
from cekit.generator.base import Generator
from cekit.version import version as cekit_version

basic_config = {'release': 1,
                'version': 1,
                'from': 'scratch',
                'name': 'testimage'}

config = Config()
config.cfg['common'] = {'redhat': True}


def print_test_name(value):
    if str(value).startswith('test'):
        return value
    return "\b"


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


@pytest.mark.parametrize('name, desc_part, exp_regex', [
    ('test_run_user',
     {'run': {'user': 1347, 'cmd': ['whoami']}}, r'.*USER 1347\n((#.*)?\n)*CMD.*'),
    ('test_default_run_user',
     {'run': {'cmd': ['whatever']}},  r'.*USER root\n((#.*)?\n)*CMD.*'),
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
     r' \\\s+COMBINED_ENV=\"set_value\" \\\s+JBOSS_IMAGE_NAME=\"testimage\" \\\s+JBOSS_IMAGE_VERSION=\"1\" \n'),
    ('test_execute',
     {'execute': [{'script': 'foo_script'}]},
     r'.*RUN [ "bash", "-x", "/tmp/scripts/testimage/foo_script" ].*'),
    ('test_execute_user',
     {'execute': [{'script': 'bar_script',
                   'user': 'bar_user'}]},
     r'.*USER bar_user\n+RUN [ "bash", "-x", "/tmp/scripts/testimage/foo_script" ].*'),
    ('test_cekit_label_version',
     {},
     r'.*io.cekit.version="%s".*' % cekit_version)],
    ids=print_test_name)
def test_dockerfile_rendering(tmpdir, name, desc_part, exp_regex):

    target = str(tmpdir.mkdir('target'))
    params = {'redhat': True}

    generator = prepare_generator(target, desc_part, 'image', 'docker', [], params)
    generator.init()
    generator.generate()

    regex_dockerfile(target, exp_regex)


@pytest.mark.parametrize('name, desc_part, exp_regex', [
    ('test_without_family',
     {}, r'JBOSS_IMAGE_NAME=\"testimage-tech-preview\"'),
    ('test_with_family',
        {'name': 'testimage/test'}, r'JBOSS_IMAGE_NAME=\"testimage-tech-preview/test\"')],
    ids=print_test_name)
def test_dockerfile_rendering_tech_preview(tmpdir, name, desc_part, exp_regex):
    target = str(tmpdir.mkdir('target'))
    params = {'redhat': True, 'tech_preview': True}
    generator = prepare_generator(target, desc_part, 'image', 'docker', [], params)
    generator.init()
    generator.generate()
    regex_dockerfile(target, exp_regex)


def test_dockerfile_docker_odcs_pulp(tmpdir, mocker):
    config.cfg['common']['redhat'] = True
    mocker.patch.object(subprocess, 'check_output', return_value=odcs_fake_resp)
    mocker.patch.object(Repository, 'fetch')
    target = str(tmpdir.mkdir('target'))
    desc_part = {'packages': {'content_sets': {
        'x86_64': 'foo'},
        'install': ['a']}}

    generator = prepare_generator(target, desc_part, 'image')
    generator.init()
    generator.generate()
    regex_dockerfile(target, 'repos/content_sets_odcs.repo')


def test_dockerfile_docker_odcs_rpm(tmpdir, mocker):
    mocker.patch.object(subprocess, 'check_output', return_value=odcs_fake_resp)
    mocker.patch.object(Repository, 'fetch')
    target = str(tmpdir.mkdir('target'))
    desc_part = {'packages': {'repositories': [{'name': 'foo',
                                                'rpm': 'foo-repo.rpm'}],
                              'install': ['a']}}

    generator = prepare_generator(target, desc_part, 'image')
    generator.init()
    generator.generate()
    regex_dockerfile(target, 'RUN yum --setopt=tsflags=nodocs install -y foo-repo.rpm')


def test_dockerfile_docker_odcs_rpm_microdnf(tmpdir, mocker):
    mocker.patch.object(subprocess, 'check_output', return_value=odcs_fake_resp)
    mocker.patch.object(Repository, 'fetch')
    target = str(tmpdir.mkdir('target'))
    desc_part = {'packages': {'repositories': [{'name': 'foo',
                                                'rpm': 'foo-repo.rpm'}],
                              'install': ['a', 'b']}}
    params = {'package_manager': 'microdnf'}

    generator = prepare_generator(target, desc_part, 'image', 'docker', [], params)
    generator.init()
    generator.generate()
    regex_dockerfile(target, 'RUN microdnf --setopt=tsflags=nodocs install -y foo-repo.rpm')
    regex_dockerfile(target, 'RUN microdnf --setopt=tsflags=nodocs install -y a b')
    regex_dockerfile(target, 'rpm -q a b')


def test_dockerfile_osbs_odcs_pulp(tmpdir, mocker):
    mocker.patch.object(subprocess, 'check_output', return_value=odcs_fake_resp)
    mocker.patch.object(Repository, 'fetch')
    config.cfg['common'] = {'redhat': True}

    target = str(tmpdir.mkdir('target'))
    os.makedirs(os.path.join(target, 'image'))
    desc_part = {'packages': {'content_sets': {
        'x86_64': 'foo'},
        'install': ['a']}}

    generator = prepare_generator(target, desc_part, 'image', 'osbs')
    generator.init()
    generator.prepare_repositories()
    with open(os.path.join(target, 'image', 'content_sets.yml'), 'r') as _file:
        content_sets = yaml.safe_load(_file)
        assert 'x86_64' in content_sets
        assert 'foo' in content_sets['x86_64']
        assert 'ppc64le' not in content_sets


def test_dockerfile_osbs_odcs_pulp_no_redhat(tmpdir, mocker):
    mocker.patch.object(subprocess, 'check_output', return_value=odcs_fake_resp)
    mocker.patch.object(Repository, 'fetch')
    config.cfg['common'] = {'redhat': False}

    target = str(tmpdir.mkdir('target'))
    desc_part = {'packages': {'repositories': [{'name': 'foo',
                                                'odcs': {
                                                    'pulp': 'rhel-7-server-rpms'
                                                }},
                                               ],
                              'install': ['a']}}

    generator = prepare_generator(target, desc_part, 'image', 'osbs')
    generator.init()
    generator.prepare_repositories()
    assert not os.path.exists(os.path.join(target, 'image', 'content_sets.yml'))


def test_dockerfile_osbs_id_redhat_false(tmpdir, mocker):
    config.cfg['common']['redhat'] = True
    mocker.patch.object(subprocess, 'check_output', return_value=odcs_fake_resp)
    mocker.patch.object(Repository, 'fetch')
    target = str(tmpdir.mkdir('target'))
    desc_part = {'packages': {'repositories': [{'name': 'foo',
                                                'id': 'foo'},
                                               ],
                              'install': ['a']}}

    generator = prepare_generator(target, desc_part, 'image', 'osbs')
    generator.init()
    generator.prepare_repositories()
    assert not os.path.exists(os.path.join(target, 'image', 'content_sets.yml'))


def test_dockerfile_osbs_url_only(tmpdir, mocker):
    mocker.patch.object(subprocess, 'check_output', return_value=odcs_fake_resp)
    mocker.patch.object(Repository, 'fetch')
    target = str(tmpdir.mkdir('target'))
    desc_part = {'packages': {'repositories': [{'name': 'foo',
                                                'url': {
                                                    'repository': 'foo'
                                                }},
                                               ],
                              'install': ['a']}}

    generator = prepare_generator(target, desc_part, 'image', 'osbs')
    generator.init()
    generator.prepare_repositories()
    assert not os.path.exists(os.path.join(target, 'image', 'content_sets.yml'))
    assert 'foo' in [x['url']['repository'] for x in generator.image['packages']['set_url']]


def test_dockerfile_osbs_odcs_rpm(tmpdir, mocker):
    mocker.patch.object(subprocess, 'check_output', return_value=odcs_fake_resp)
    mocker.patch.object(Repository, 'fetch')
    target = str(tmpdir.mkdir('target'))
    desc_part = {'packages': {'repositories': [{'name': 'foo',
                                                'rpm': 'foo-repo.rpm'}],
                              'install': ['a']}}

    generator = prepare_generator(target, desc_part, 'image', 'osbs')
    generator.init()
    generator.generate()
    regex_dockerfile(target, 'RUN yum --setopt=tsflags=nodocs install -y foo-repo.rpm')


def test_dockerfile_osbs_odcs_rpm_microdnf(tmpdir, mocker):
    mocker.patch.object(subprocess, 'check_output', return_value=odcs_fake_resp)
    mocker.patch.object(Repository, 'fetch')
    target = str(tmpdir.mkdir('target'))
    desc_part = {'packages': {'repositories': [{'name': 'foo',
                                                'rpm': 'foo-repo.rpm'}],
                              'install': ['a']}}
    params = {'package_manager': 'microdnf'}

    generator = prepare_generator(target, desc_part, 'image', 'osbs', [], params)
    generator.init()
    generator.generate()
    regex_dockerfile(target, 'RUN microdnf --setopt=tsflags=nodocs install -y foo-repo.rpm')
    regex_dockerfile(target, 'RUN microdnf --setopt=tsflags=nodocs install -y a')
    regex_dockerfile(target, 'rpm -q a')


# https://github.com/cekit/cekit/issues/406
def test_dockerfile_do_not_copy_modules_if_no_modules(tmpdir, mocker):
    target = str(tmpdir.mkdir('target'))
    generator = prepare_generator(target, {})
    generator.init()
    generator.generate()
    regex_dockerfile(target, '^((?!COPY modules /tmp/scripts/))')


# https://github.com/cekit/cekit/issues/406
def test_dockerfile_copy_modules_if_modules_defined(tmpdir, mocker):
    target = str(tmpdir.mkdir('target'))
    config.cfg['common']['work_dir'] = os.path.dirname(target)
    module_dir = os.path.join(os.path.dirname(target), 'modules', 'foo')
    module_yaml_path = os.path.join(module_dir, 'module.yaml')

    os.makedirs(module_dir)

    with open(module_yaml_path, 'w') as outfile:
        yaml.dump({'name': 'foo'}, outfile, default_flow_style=False)

    generator = prepare_generator(
        target, {'modules': {'repositories': [{'name': 'modules',
                                               'path': 'modules'}],
                             'install': [{'name': 'foo'}]}})
    generator.init()
    generator.generate()
    regex_dockerfile(target, 'COPY modules /tmp/scripts/')


def prepare_generator(target, desc_part, desc_type="image", engine="docker", overrides=[], params={}):
    # create basic descriptor

    desc = basic_config.copy()
    desc.update(desc_part)

    tmp_image_file = os.path.join(os.path.dirname(target), 'image.yaml')
    with open(tmp_image_file, 'w') as outfile:
        yaml.dump(desc, outfile, default_flow_style=False)

    generator = Generator(tmp_image_file, target, engine, overrides, params)
    generator._content_set_f = os.path.join(target, 'image', 'content_sets.yml')
    generator._container_f = os.path.join(target, 'image', 'container.yaml')
    return generator


def regex_dockerfile(target, exp_regex):
    with open(os.path.join(target, 'image', 'Dockerfile'), "r") as fd:
        dockerfile_content = fd.read()
        regex = re.compile(exp_regex, re.MULTILINE)
        assert regex.search(dockerfile_content)
